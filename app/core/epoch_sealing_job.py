"""Background job: seal integrity epochs that are due (time or event count) and open next epoch."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.application.integrity_config import INTEGRITY_PROFILE_CONFIG
from app.domain.enums import IntegrityProfile
from app.infrastructure.external.tsa.client import TsaClient
from app.infrastructure.external.tsa.config import TsaConfig

logger = logging.getLogger(__name__)

SEAL_POLL_INTERVAL_SECONDS = 30


async def run_epoch_sealing_job(
    http_client: Any,
    session_factory: Callable[[], Any],
    settings: Any,
) -> None:
    """Loop: every SEAL_POLL_INTERVAL_SECONDS, seal due epochs and open next.

    Uses FOR UPDATE SKIP LOCKED. TSA anchoring for COMPLIANCE/LEGAL_GRADE.
    Cancelling the task stops the loop.

    Args:
        http_client: httpx.AsyncClient (or protocol) for TSA requests.
        session_factory: Callable that returns an async context manager for AsyncSession.
        settings: Application settings (chain_anchor_tsa_url, etc.).
    """
    await asyncio.sleep(60)  # initial delay so server can settle

    tsa_config = TsaConfig(
        url=settings.chain_anchor_tsa_url,
        timeout_seconds=settings.chain_anchor_tsa_timeout_seconds,
        cert_path=settings.chain_anchor_tsa_cert_path,
        hashname="sha256",
    )
    tsa_client = TsaClient(config=tsa_config, http_client=http_client)

    from app.infrastructure.persistence.repositories import (
        EventRepository,
        IntegrityEpochRepository,
        MerkleNodeRepository,
        TsaAnchorRepository,
        TenantRepository,
    )
    from app.infrastructure.services.tsa_service import TsaService
    from app.application.services.merkle_service import MerkleService

    while True:
        try:
            if session_factory is None:
                logger.error("Epoch sealing job: database not configured")
                await asyncio.sleep(SEAL_POLL_INTERVAL_SECONDS)
                continue

            if http_client is None:
                logger.error(
                    "Epoch sealing job: http_client is None; will retry on next poll"
                )
                await asyncio.sleep(SEAL_POLL_INTERVAL_SECONDS)
                continue

            # Process one epoch per transaction to avoid holding locks during TSA calls.
            while True:
                async with session_factory() as db:
                    async with db.begin():
                        epoch_repo = IntegrityEpochRepository(db)
                        event_repo = EventRepository(db)
                        tenant_repo = TenantRepository(db, cache_service=None, audit_service=None)
                        merkle_repo = MerkleNodeRepository(db)
                        tsa_anchor_repo = TsaAnchorRepository(db)
                        tsa_service = TsaService(
                            tsa_client=tsa_client,
                            tsa_anchor_repo=tsa_anchor_repo,
                            tsa_provider_url=settings.chain_anchor_tsa_url,
                        )
                        sealable = await epoch_repo.get_sealable_epochs(limit=1)
                        if not sealable:
                            break
                        epoch = sealable[0]
                        try:
                            last_ev = await event_repo.get_last_event_in_epoch(
                                epoch.id, epoch.tenant_id
                            )
                            if not last_ev:
                                logger.warning(
                                    "Epoch %s has no events, sealing with genesis_hash",
                                    epoch.id,
                                )
                                terminal_hash = epoch.genesis_hash or ""
                            else:
                                terminal_hash = last_ev.hash

                            merkle_root: str | None = None
                            tsa_anchor_id: str | None = None
                            config = INTEGRITY_PROFILE_CONFIG.get(
                                IntegrityProfile(epoch.profile_snapshot)
                            )
                            if config and config.merkle_enabled:
                                merkle_service = MerkleService(
                                    event_repo=event_repo,
                                    merkle_repo=merkle_repo,
                                )
                                try:
                                    merkle_root = await merkle_service.build_and_store(
                                        epoch.tenant_id, epoch
                                    )
                                except Exception as e:
                                    logger.warning(
                                        "Merkle build failed for epoch %s: %s",
                                        epoch.id,
                                        e,
                                        exc_info=True,
                                    )
                                    # Profile requires Merkle; do not seal without root.
                                    raise
                            if config and config.tsa_enabled:
                                try:
                                    tsa_anchor_id = await tsa_service.anchor(
                                        epoch.tenant_id,
                                        merkle_root or terminal_hash,
                                        "EPOCH",
                                    )
                                except Exception as e:
                                    logger.warning(
                                        "TSA anchor failed for epoch %s: %s",
                                        epoch.id,
                                        e,
                                        exc_info=True,
                                    )
                                    # LEGAL_GRADE/COMPLIANCE: do not seal without TSA anchor.
                                    raise
                            await epoch_repo.seal_epoch(
                                epoch.id,
                                terminal_hash,
                                tsa_anchor_id=tsa_anchor_id,
                                merkle_root=merkle_root,
                            )
                            # Use current tenant profile for next epoch (not stale snapshot).
                            tenant = await tenant_repo.get_by_id(epoch.tenant_id)
                            next_profile = (
                                tenant.integrity_profile.value
                                if tenant
                                else epoch.profile_snapshot
                            )
                            next_num = epoch.epoch_number + 1
                            await epoch_repo.create_epoch(
                                tenant_id=epoch.tenant_id,
                                subject_id=epoch.subject_id,
                                epoch_number=next_num,
                                genesis_hash=terminal_hash,
                                profile_snapshot=next_profile,
                            )
                        except Exception:
                            logger.exception(
                                "Failed to seal epoch %s",
                                epoch.id,
                            )
                            raise

        except asyncio.CancelledError:
            logger.info("Epoch sealing job cancelled, shutting down")
            raise
        except Exception:
            logger.exception("Epoch sealing job encountered a fatal error")

        await asyncio.sleep(SEAL_POLL_INTERVAL_SECONDS)
