"""Background job: seal integrity epochs that are due (time or event count) and open next epoch."""

import asyncio
import logging

from fastapi import FastAPI

from app.application.integrity_config import INTEGRITY_PROFILE_CONFIG
from app.core.config import get_settings
from app.domain.enums import IntegrityProfile
from app.infrastructure.external.tsa.client import TsaClient
from app.infrastructure.external.tsa.config import TsaConfig
from app.infrastructure.persistence.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

SEAL_POLL_INTERVAL_SECONDS = 30


async def run_epoch_sealing_job(app: FastAPI) -> None:
    """Loop: every SEAL_POLL_INTERVAL_SECONDS, seal due epochs and open next.

    Uses FOR UPDATE SKIP LOCKED. TSA anchoring for COMPLIANCE/LEGAL_GRADE.
    Cancelling the task stops the loop.
    """
    settings = get_settings()
    await asyncio.sleep(60)  # initial delay so server can settle

    http_client = getattr(app.state, "oauth_http_client", None)
    if http_client is None:
        logger.warning("Epoch sealing job: no oauth_http_client on app.state, skipping")
        return

    tsa_config = TsaConfig(
        url=settings.chain_anchor_tsa_url,
        timeout_seconds=settings.chain_anchor_tsa_timeout_seconds,
        cert_path=settings.chain_anchor_tsa_cert_path,
        hashname="sha256",
    )
    tsa_client = TsaClient(config=tsa_config, http_client=http_client)

    from app.infrastructure.persistence.repositories import (
        IntegrityEpochRepository,
        TsaAnchorRepository,
    )
    from app.infrastructure.services.tsa_service import TsaService

    while True:
        try:
            if AsyncSessionLocal is None:
                logger.error("Epoch sealing job: database not configured")
                await asyncio.sleep(SEAL_POLL_INTERVAL_SECONDS)
                continue

            # Process one epoch per transaction to avoid holding locks during TSA calls.
            while True:
                async with AsyncSessionLocal() as db:
                    async with db.begin():
                        epoch_repo = IntegrityEpochRepository(db)
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
                            last_ev = await epoch_repo.get_last_event_in_epoch(
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
                            tsa_anchor_id: str | None = None
                            config = INTEGRITY_PROFILE_CONFIG.get(
                                IntegrityProfile(epoch.profile_snapshot)
                            )
                            if config and config.tsa_enabled:
                                try:
                                    tsa_anchor_id = await tsa_service.anchor(
                                        epoch.tenant_id,
                                        terminal_hash,
                                        "EPOCH",
                                    )
                                except Exception as e:
                                    logger.warning(
                                        "TSA anchor failed for epoch %s: %s",
                                        epoch.id,
                                        e,
                                        exc_info=True,
                                    )
                            await epoch_repo.seal_epoch(
                                epoch.id,
                                terminal_hash,
                                tsa_anchor_id=tsa_anchor_id,
                            )
                            next_num = epoch.epoch_number + 1
                            await epoch_repo.create_epoch(
                                tenant_id=epoch.tenant_id,
                                subject_id=epoch.subject_id,
                                epoch_number=next_num,
                                genesis_hash=terminal_hash,
                                profile_snapshot=epoch.profile_snapshot,
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
