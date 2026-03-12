"""Epoch service: get-or-create open integrity epoch per (tenant, subject)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.integrity import OpenEpochAssignment
from app.domain.enums import IntegrityProfile

if TYPE_CHECKING:
    from app.application.interfaces.repositories import IEpochRepository, ITenantRepository


class EpochService:
    """Resolves or creates the open integrity epoch for a (tenant, subject) and returns assignment."""

    def __init__(
        self,
        epoch_repo: IEpochRepository,
        tenant_repo: ITenantRepository,
    ) -> None:
        self._epoch_repo = epoch_repo
        self._tenant_repo = tenant_repo

    async def get_or_create_open_epoch(
        self,
        tenant_id: str,
        subject_id: str,
    ) -> OpenEpochAssignment:
        """Return the open epoch for (tenant, subject), creating one if none exists.

        Caller must call epoch_repo.increment_epoch_event(epoch_id, event_seq, is_first=(event_count==0))
        after persisting the event.
        """
        existing = await self._epoch_repo.get_open_epoch_for_update(
            tenant_id, subject_id
        )
        if existing is not None:
            return existing

        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")
        profile = tenant.integrity_profile
        profile_snapshot = (
            profile.value if isinstance(profile, IntegrityProfile) else profile
        )

        next_number = await self._epoch_repo.get_next_epoch_number(
            tenant_id, subject_id
        )
        genesis_hash = await self._epoch_repo.get_latest_sealed_terminal_hash(
            tenant_id, subject_id
        ) or "GENESIS"

        return await self._epoch_repo.create_epoch(
            tenant_id=tenant_id,
            subject_id=subject_id,
            epoch_number=next_number,
            genesis_hash=genesis_hash,
            profile_snapshot=profile_snapshot,
        )

    async def record_event_appended(
        self,
        epoch_id: str,
        event_seq: int,
        is_first: bool,
    ) -> None:
        """Record that an event was appended to the epoch (call after persisting the event)."""
        await self._epoch_repo.increment_epoch_event(
            epoch_id,
            event_seq,
            is_first=is_first,
        )
