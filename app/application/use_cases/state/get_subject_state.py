"""Get current (or as-of) state for a subject by replaying events."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.application.dtos.event import EventResult
from app.application.dtos.state import StateResult
from app.application.interfaces.repositories import (
    IEventRepository,
    ISubjectRepository,
    ISubjectSnapshotRepository,
)
from app.domain.exceptions import ResourceNotFoundException


def _apply_event(state: dict[str, Any], event: EventResult) -> None:
    """Update state by applying a single event (merge payload into state)."""
    for key, value in event.payload.items():
        state[key] = value


class GetSubjectStateUseCase:
    """Derive subject state from event log (replay). Uses snapshot + tail when available."""

    def __init__(
        self,
        event_repo: IEventRepository,
        subject_repo: ISubjectRepository,
        snapshot_repo: ISubjectSnapshotRepository | None = None,
    ) -> None:
        self._event_repo = event_repo
        self._subject_repo = subject_repo
        self._snapshot_repo = snapshot_repo

    async def get_current_state(
        self,
        tenant_id: str,
        subject_id: str,
        as_of: str | None = None,
    ) -> StateResult:
        """Return derived state by replaying events in order. Optionally filter by as_of (ISO8601 datetime). Uses snapshot + tail when available."""
        from datetime import datetime

        subject = await self._subject_repo.get_by_id_and_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)

        as_of_dt: datetime | None = None
        if as_of:
            as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))

        snapshot = None
        if self._snapshot_repo:
            snapshot = await self._snapshot_repo.get_latest_by_subject(
                subject_id=subject_id,
                tenant_id=tenant_id,
            )

        if snapshot:
            snapshot_event = await self._event_repo.get_by_id(
                snapshot.snapshot_at_event_id
            )
            use_snapshot = True
            if as_of_dt is not None and snapshot_event:
                if snapshot_event.event_time > as_of_dt:
                    use_snapshot = False
            if use_snapshot and snapshot_event and snapshot_event.tenant_id == tenant_id:
                state = deepcopy(snapshot.state_json)
                tail = await self._event_repo.get_events_chronological(
                    subject_id=subject_id,
                    tenant_id=tenant_id,
                    as_of=as_of_dt,
                    after_event_id=snapshot.snapshot_at_event_id,
                )
                for event in tail:
                    _apply_event(state, event)
                last_event_id = tail[-1].id if tail else snapshot.snapshot_at_event_id
                event_count = snapshot.event_count_at_snapshot + len(tail)
                return StateResult(
                    state=state,
                    last_event_id=last_event_id,
                    event_count=event_count,
                )

        events = await self._event_repo.get_events_chronological(
            subject_id=subject_id,
            tenant_id=tenant_id,
            as_of=as_of_dt,
        )

        state: dict[str, Any] = {}
        last_event_id: str | None = None
        for event in events:
            _apply_event(state, event)
            last_event_id = event.id

        return StateResult(
            state=state,
            last_event_id=last_event_id,
            event_count=len(events),
        )
