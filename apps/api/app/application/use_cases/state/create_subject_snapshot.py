"""Create or update subject snapshot (on-demand checkpoint for state derivation)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.subject_snapshot import SubjectSnapshotResult
from app.domain.exceptions import ResourceNotFoundException, ValidationException

if TYPE_CHECKING:
    from app.application.interfaces.repositories import ISubjectSnapshotRepository
    from app.application.use_cases.state.get_subject_state import GetSubjectStateUseCase


class CreateSubjectSnapshotUseCase:
    """Creates or replaces the snapshot for a subject by running state derivation and persisting the result."""

    def __init__(
        self,
        state_use_case: "GetSubjectStateUseCase",
        snapshot_repo: "ISubjectSnapshotRepository",
    ) -> None:
        self._state_use_case = state_use_case
        self._snapshot_repo = snapshot_repo

    async def create_snapshot(
        self, tenant_id: str, subject_id: str
    ) -> SubjectSnapshotResult:
        """Compute current state via event replay and persist as snapshot.

        Uses get_current_state (which may use an existing snapshot + tail) then
        creates or replaces the subject's snapshot row. Fails if the subject
        has no events (snapshot requires at least one event for snapshot_at_event_id).

        Returns:
            The created or updated snapshot result.

        Raises:
            ResourceNotFoundException: Subject not found in tenant.
            ValidationException: Subject has no events (cannot create snapshot).
        """
        state_result = await self._state_use_case.get_current_state(
            tenant_id=tenant_id,
            subject_id=subject_id,
            as_of=None,
        )
        if state_result.last_event_id is None:
            raise ValidationException(
                "Cannot create snapshot: subject has no events. "
                "Add at least one event before creating a snapshot."
            )
        return await self._snapshot_repo.create_snapshot(
            subject_id=subject_id,
            tenant_id=tenant_id,
            snapshot_at_event_id=state_result.last_event_id,
            state_json=state_result.state,
            event_count_at_snapshot=state_result.event_count,
        )
