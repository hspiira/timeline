"""Epoch service: get-or-create open integrity epoch per (tenant, subject)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from app.application.dtos.event import EventResult
from app.application.dtos.integrity import OpenEpochAssignment

if TYPE_CHECKING:
    from typing import Awaitable

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

        Prefer with_open_epoch() when appending an event so record_event_appended is
        guaranteed. This method is for read-only resolution or bulk flows that call
        record_events_appended_bulk after persisting.
        """
        existing = await self._epoch_repo.get_open_epoch_for_update(
            tenant_id, subject_id
        )
        if existing is not None:
            return existing

        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")
        profile_snapshot = tenant.integrity_profile.value

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

    async def with_open_epoch(
        self,
        tenant_id: str,
        subject_id: str,
        append_fn: Callable[
            [OpenEpochAssignment], "Awaitable[tuple[EventResult, bool]]"
        ],
    ) -> tuple[OpenEpochAssignment, EventResult]:
        """Get or create open epoch, run append_fn(assignment), then record_event_appended.

        Ensures increment_epoch_event is always called after a successful append.
        append_fn must persist the event and return (event_result, is_first).
        """
        assignment = await self.get_or_create_open_epoch(tenant_id, subject_id)
        created, is_first = await append_fn(assignment)
        if created.event_seq is not None:
            await self._epoch_repo.increment_epoch_event(
                assignment.epoch_id,
                created.event_seq,
                is_first=is_first,
            )
        return assignment, created

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

    async def record_events_appended_bulk(
        self, entries: list[tuple[str, int, bool]]
    ) -> None:
        """Record multiple event appends. Each entry is (epoch_id, event_seq, is_first)."""
        for epoch_id, event_seq, is_first in entries:
            await self._epoch_repo.increment_epoch_event(
                epoch_id, event_seq, is_first=is_first
            )
