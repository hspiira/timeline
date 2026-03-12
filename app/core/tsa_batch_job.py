"""Background job: batch TSA anchoring for COMPLIANCE profile events.

Event write path enqueues COMPLIANCE events into an in-memory queue.
This worker drains the queue periodically, computes a batch hash per tenant,
anchors it via TSA, and updates events with tsa_anchor_id + integrity_status=VALID.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import defaultdict
from typing import Iterable

from fastapi import FastAPI

from app.application.services.tsa_batch_queue import DEFAULT_TSA_BATCH_QUEUE, TsaBatchItem
from app.core.config import get_settings
from app.domain.enums import TsaAnchorType
from app.infrastructure.external.tsa.client import TsaClient
from app.infrastructure.external.tsa.config import TsaConfig
from app.infrastructure.persistence.database import AsyncSessionLocal
from app.infrastructure.persistence.repositories import EventRepository, TsaAnchorRepository
from app.infrastructure.services.tsa_service import TsaService

logger = logging.getLogger(__name__)


def _group_by_tenant(items: Iterable[TsaBatchItem]) -> dict[str, list[TsaBatchItem]]:
    grouped: dict[str, list[TsaBatchItem]] = defaultdict(list)
    for item in items:
        grouped[item.tenant_id].append(item)
    return grouped


async def run_tsa_batch_job(app: FastAPI) -> None:
    """Loop: drain TSA batch queue and anchor batches via TSA.

    - Drains up to tsa_batch_max_events items per interval.
    - Groups by tenant, computes deterministic batch hash per tenant, anchors as BATCH.
    - Updates events with tsa_anchor_id and integrity_status=VALID.
    """
    settings = get_settings()
    if not getattr(settings, "tsa_batch_enabled", False):
        logger.info("TSA batch job disabled via config")
        return

    await asyncio.sleep(30)  # allow app startup to settle

    http_client = getattr(app.state, "oauth_http_client", None)
    if http_client is None:
        logger.warning("TSA batch job: no oauth_http_client on app.state, skipping")
        return

    tsa_config = TsaConfig(
        url=settings.chain_anchor_tsa_url,
        timeout_seconds=settings.chain_anchor_tsa_timeout_seconds,
        cert_path=settings.chain_anchor_tsa_cert_path,
        hashname="sha256",
    )
    tsa_client = TsaClient(config=tsa_config, http_client=http_client)

    while True:
        try:
            if AsyncSessionLocal is None:
                logger.error("TSA batch job: database not configured")
                await asyncio.sleep(settings.tsa_batch_interval_seconds)
                continue

            items = await DEFAULT_TSA_BATCH_QUEUE.drain(settings.tsa_batch_max_events)
            if not items:
                await asyncio.sleep(settings.tsa_batch_interval_seconds)
                continue

            grouped = _group_by_tenant(items)
            for tenant_id, tenant_items in grouped.items():
                try:
                    # Deterministic batch hash: sort by event_id then hash and concatenate.
                    sorted_items = sorted(
                        tenant_items, key=lambda it: (it.event_id, it.payload_hash_hex)
                    )
                    payload = "".join(it.payload_hash_hex for it in sorted_items).encode(
                        "ascii"
                    )
                    batch_hash = hashlib.sha256(payload).hexdigest()

                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            tsa_anchor_repo = TsaAnchorRepository(db)
                            event_repo = EventRepository(db)
                            tsa_service = TsaService(
                                tsa_client=tsa_client,
                                tsa_anchor_repo=tsa_anchor_repo,
                                tsa_provider_url=settings.chain_anchor_tsa_url,
                            )
                            anchor_id = await tsa_service.anchor(
                                tenant_id, batch_hash, TsaAnchorType.BATCH
                            )
                            event_ids = [it.event_id for it in sorted_items]
                            await event_repo.set_tsa_anchor_for_events(
                                tenant_id=tenant_id,
                                event_ids=event_ids,
                                tsa_anchor_id=anchor_id,
                            )
                except Exception:
                    logger.exception(
                        "TSA batch anchoring failed for tenant_id=%s; re-queuing %s items",
                        tenant_id,
                        len(tenant_items),
                    )
                    # Re-enqueue failed tenant batch so it can be retried on the next cycle.
                    for item in tenant_items:
                        await DEFAULT_TSA_BATCH_QUEUE.enqueue(item)
        except asyncio.CancelledError:
            logger.info("TSA batch job cancelled, shutting down")
            raise
        except Exception:
            logger.exception("TSA batch job encountered a fatal error")

        await asyncio.sleep(settings.tsa_batch_interval_seconds)

