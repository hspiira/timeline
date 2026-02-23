"""Get current (or as-of) state for a subject by replaying events."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from app.application.dtos.event import EventResult
from app.application.dtos.state import StateResult
from app.application.interfaces.repositories import (
    IEventRepository,
    ISubjectRepository,
    ISubjectSnapshotRepository,
)
from app.domain.exceptions import ResourceNotFoundException, ValidationException


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
        workflow_instance_id: str | None = None,
    ) -> StateResult:
        """Return derived state by replaying events in order. Optionally filter by as_of (ISO8601 datetime) and workflow_instance_id (stream). When workflow_instance_id is set, snapshot is not used (replay only for that stream)."""

        subject = await self._subject_repo.get_by_id_and_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)

        as_of_dt: datetime | None = None
        if as_of:
            try:
                as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValidationException(
                    f"Invalid as_of datetime: {as_of!r}. Expected ISO8601 (e.g. 2024-01-15T12:00:00Z)."
                ) from e

        # When scoping to a stream, do not use snapshot (snapshots are subject-scoped).
        snapshot = None
        if self._snapshot_repo and workflow_instance_id is None:
            snapshot = await self._snapshot_repo.get_latest_by_subject(
                subject_id=subject_id,
                tenant_id=tenant_id,
            )

        # If we have a snapshot, try snapshot + tail. snapshot_event from get_by_id_and_tenant may be
        # None (e.g. referenced event was deleted or wrong tenant); or use_snapshot may be False for as_of.
        # In those cases the condition below fails and we fall through to full replay.
        if snapshot:
            snapshot_event = await self._event_repo.get_by_id_and_tenant(
                snapshot.snapshot_at_event_id, tenant_id
            )
            use_snapshot = True
            if as_of_dt is not None and snapshot_event:
                if snapshot_event.event_time > as_of_dt:
                    use_snapshot = False
            if use_snapshot and snapshot_event:
                state = deepcopy(snapshot.state_json)
                tail = await self._event_repo.get_events_chronological(
                    subject_id=subject_id,
                    tenant_id=tenant_id,
                    as_of=as_of_dt,
                    after_event_id=snapshot.snapshot_at_event_id,
                    workflow_instance_id=workflow_instance_id,
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
            workflow_instance_id=workflow_instance_id,
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
