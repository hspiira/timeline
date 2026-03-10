"""Background job: anchor chain tips to RFC 3161 TSA (trusted timestamping)."""

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from app.core.config import get_settings
from app.infrastructure.external.tsa.client import TsaClient
from app.infrastructure.external.tsa.config import TsaConfig
from app.infrastructure.persistence.database import (
    AsyncSessionLocal,
    _ensure_engine,
)

logger = logging.getLogger(__name__)


async def run_chain_anchor_job(app: FastAPI) -> None:
    """Loop: every chain_anchor_interval_seconds, anchor chain tips for each tenant with events.

    Uses app.state.oauth_http_client for TSA POST. Cancelling the task stops the loop.
    """
    settings = get_settings()
    await asyncio.sleep(60)  # initial delay so server can settle on startup

    http_client = getattr(app.state, "oauth_http_client", None)
    if http_client is None:
        logger.warning("Chain anchor job: no oauth_http_client on app.state, skipping")
        return

    tsa_config = TsaConfig(
        url=settings.chain_anchor_tsa_url,
        timeout_seconds=settings.chain_anchor_tsa_timeout_seconds,
        cert_path=settings.chain_anchor_tsa_cert_path,
        hashname="sha256",
    )
    tsa_client = TsaClient(config=tsa_config, http_client=http_client)

    from app.application.use_cases.anchoring import AnchorChainTipsUseCase
    from app.infrastructure.persistence.repositories import (
        ChainAnchorRepository,
        EventRepository,
    )

    while True:
        try:
            _ensure_engine()
            if AsyncSessionLocal is None:
                logger.error("Chain anchor job: database not configured")
                await asyncio.sleep(settings.chain_anchor_interval_seconds)
                continue

            async with AsyncSessionLocal() as db:
                event_repo = EventRepository(db)
                tenant_ids = await event_repo.get_distinct_tenant_ids()
            for tenant_id in tenant_ids:
                try:
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            event_repo = EventRepository(db)
                            anchor_repo = ChainAnchorRepository(db)
                            use_case = AnchorChainTipsUseCase(
                                event_repo=event_repo,
                                anchor_repo=anchor_repo,
                                tsa_client=tsa_client,
                                tsa_url=settings.chain_anchor_tsa_url,
                            )
                            await use_case.run_for_tenant(tenant_id)
                except Exception:
                    logger.exception(
                        "Anchor failed for tenant_id=%s",
                        tenant_id,
                    )
        except Exception:
            logger.exception("Chain anchor job encountered a fatal error")

        await asyncio.sleep(settings.chain_anchor_interval_seconds)
