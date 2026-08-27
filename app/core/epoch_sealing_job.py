"""Background job: seal integrity epochs that are due (time or event count) and open next epoch."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.application.integrity_config import (
    EPOCH_SEAL_MAX_RETRIES,
    INTEGRITY_PROFILE_CONFIG,
    IntegrityProfileConfig,
)
from app.application.services.merkle_service import MerkleService
from app.domain.enums import IntegrityProfile, TsaAnchorType
from app.infrastructure.external.tsa.client import TsaClient
from app.infrastructure.external.tsa.config import TsaConfig
from app.infrastructure.persistence.repositories import (
    EventRepository,
    IntegrityEpochRepository,
    MerkleNodeRepository,
    TsaAnchorRepository,
    TenantRepository,
)
from app.infrastructure.services.tsa_service import TsaService

logger = logging.getLogger(__name__)

SEAL_POLL_INTERVAL_SECONDS = 30

SEAL_BATCH_SIZE = 10


@dataclass(frozen=True)
class _SealingRepos:
    """The repositories and services used to seal epochs inside one transaction."""

    epoch_repo: IntegrityEpochRepository
    event_repo: EventRepository
    tenant_repo: TenantRepository
    merkle_repo: MerkleNodeRepository
    tsa_service: TsaService


def _build_repos(db: Any, tsa_client: TsaClient, settings: Any) -> _SealingRepos:
    """Construct the per-transaction repositories bound to one session."""
    tsa_anchor_repo = TsaAnchorRepository(db)
    return _SealingRepos(
        epoch_repo=IntegrityEpochRepository(db),
        event_repo=EventRepository(db),
        tenant_repo=TenantRepository(db, cache_service=None, audit_service=None),
        merkle_repo=MerkleNodeRepository(db),
        tsa_service=TsaService(
            tsa_client=tsa_client,
            tsa_anchor_repo=tsa_anchor_repo,
            tsa_provider_url=settings.chain_anchor_tsa_url,
        ),
    )


async def _terminal_hash_for(repos: _SealingRepos, epoch: Any) -> str:
    """The hash the epoch seals on: its last event, or its genesis if it holds none."""
    last_ev = await repos.event_repo.get_last_event_in_epoch(epoch.id, epoch.tenant_id)
    if last_ev:
        return last_ev.hash
    logger.warning("Epoch %s has no events, sealing with genesis_hash", epoch.id)
    return epoch.genesis_hash or ""


async def _build_merkle_root(
    repos: _SealingRepos, epoch: Any, config: IntegrityProfileConfig | None
) -> str | None:
    """Build the Merkle root when the profile requires one. Never seals without it."""
    if not (config and config.merkle_enabled):
        return None
    merkle_service = MerkleService(
        event_repo=repos.event_repo,
        merkle_repo=repos.merkle_repo,
    )
    try:
        return await merkle_service.build_and_store(epoch.tenant_id, epoch)
    except Exception as e:
        logger.warning(
            "Merkle build failed for epoch %s: %s", epoch.id, e, exc_info=True
        )
        # Profile requires Merkle; do not seal without root.
        raise


async def _anchor_epoch(
    repos: _SealingRepos,
    epoch: Any,
    config: IntegrityProfileConfig | None,
    anchored_hash: str,
) -> str | None:
    """Timestamp the epoch with the TSA when the profile requires it."""
    if not (config and config.tsa_enabled):
        return None
    try:
        return await repos.tsa_service.anchor(
            epoch.tenant_id, anchored_hash, TsaAnchorType.EPOCH
        )
    except Exception as e:
        logger.warning("TSA anchor failed for epoch %s: %s", epoch.id, e, exc_info=True)
        # LEGAL_GRADE/COMPLIANCE: do not seal without TSA anchor.
        raise


async def _open_next_epoch(repos: _SealingRepos, epoch: Any, terminal_hash: str) -> None:
    """Chain a fresh open epoch onto the one just sealed."""
    # Use current tenant profile for next epoch (not stale snapshot).
    tenant = await repos.tenant_repo.get_by_id(epoch.tenant_id)
    next_profile = (
        tenant.integrity_profile.value if tenant else epoch.profile_snapshot
    )
    await repos.epoch_repo.create_epoch(
        tenant_id=epoch.tenant_id,
        subject_id=epoch.subject_id,
        epoch_number=epoch.epoch_number + 1,
        genesis_hash=terminal_hash,
        profile_snapshot=next_profile,
    )


async def _seal_one_epoch(repos: _SealingRepos, epoch: Any) -> None:
    """Seal one epoch and open its successor. Raises if any required step fails."""
    terminal_hash = await _terminal_hash_for(repos, epoch)
    config = INTEGRITY_PROFILE_CONFIG.get(IntegrityProfile(epoch.profile_snapshot))
    merkle_root = await _build_merkle_root(repos, epoch, config)
    tsa_anchor_id = await _anchor_epoch(
        repos, epoch, config, merkle_root or terminal_hash
    )
    await repos.epoch_repo.seal_epoch(
        epoch.id,
        terminal_hash,
        tsa_anchor_id=tsa_anchor_id,
        merkle_root=merkle_root,
    )
    # seal_epoch resets seal_retry_count so no in-memory state to clear.
    await _open_next_epoch(repos, epoch, terminal_hash)


async def _record_seal_failure(repos: _SealingRepos, epoch: Any) -> None:
    """Count a failed attempt, and give up on the epoch once it has used them all."""
    try:
        new_count = await repos.epoch_repo.increment_seal_retry_count(epoch.id)
        if new_count >= EPOCH_SEAL_MAX_RETRIES:
            logger.error(
                "Failed to seal epoch %s after %s attempts; marking as FAILED",
                epoch.id,
                new_count,
            )
            await repos.epoch_repo.mark_epoch_failed(epoch.id)
        else:
            logger.exception(
                "Failed to seal epoch %s (attempt %s); will retry",
                epoch.id,
                new_count,
            )
    except Exception as persist_err:
        logger.exception(
            "Failed to persist seal retry count or mark epoch FAILED for %s: %s",
            epoch.id,
            persist_err,
        )


async def _seal_batch(repos: _SealingRepos, epochs: list[Any]) -> None:
    """Seal every epoch in the batch; one failure must not stop the others."""
    for epoch in epochs:
        try:
            await _seal_one_epoch(repos, epoch)
        except Exception:
            await _record_seal_failure(repos, epoch)


async def _seal_due_epochs(
    session_factory: Callable[[], Any], tsa_client: TsaClient, settings: Any
) -> None:
    """Drain the sealable epochs a batch at a time, one transaction per batch."""
    while True:
        async with session_factory() as db:
            async with db.begin():
                repos = _build_repos(db, tsa_client, settings)
                # Fetch a batch of sealable epochs to avoid single-epoch stalls.
                sealable = await repos.epoch_repo.get_sealable_epochs(
                    limit=SEAL_BATCH_SIZE
                )
                if not sealable:
                    return
                await _seal_batch(repos, sealable)


def _can_run(session_factory: Callable[[], Any] | None, http_client: Any) -> bool:
    """Whether this poll can do any work. Logs why not, and retries on the next one."""
    if session_factory is None:
        logger.error("Epoch sealing job: database not configured")
        return False
    if http_client is None:
        logger.error("Epoch sealing job: http_client is None; will retry on next poll")
        return False
    return True


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

    while True:
        try:
            if _can_run(session_factory, http_client):
                await _seal_due_epochs(session_factory, tsa_client, settings)
        except asyncio.CancelledError:
            logger.info("Epoch sealing job cancelled, shutting down")
            raise
        except Exception:
            logger.exception("Epoch sealing job encountered a fatal error")

        await asyncio.sleep(SEAL_POLL_INTERVAL_SECONDS)
