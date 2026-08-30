"""Run batch snapshot job: create or update snapshots for subjects in a tenant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.subject_snapshot import SnapshotRunResult
from app.domain.exceptions import ResourceNotFoundException, ValidationException

if TYPE_CHECKING:
    from app.application.interfaces.repositories import ISubjectRepository
    from app.application.use_cases.state.create_subject_snapshot import (
        CreateSubjectSnapshotUseCase,
    )

SNAPSHOT_JOB_PAGE_SIZE = 100
SNAPSHOT_JOB_DEFAULT_LIMIT = 500
SNAPSHOT_JOB_MAX_LIMIT = 2000
MAX_ERROR_SUBJECT_IDS = 50


class RunSnapshotJobUseCase:
    """Creates or updates snapshots for subjects in the tenant (paginated).

    Lists subjects via get_by_tenant; for each subject calls
    CreateSubjectSnapshotUseCase.create_snapshot. Counts success, skipped (no events),
    and errors; returns a summary. One snapshot per subject (replace if exists).
    """

    def __init__(
        self,
        subject_repo: "ISubjectRepository",
        create_snapshot_use_case: "CreateSubjectSnapshotUseCase",
    ) -> None:
        self._subject_repo = subject_repo
        self._create_snapshot_use_case = create_snapshot_use_case

    async def run(
        self, tenant_id: str, limit: int = SNAPSHOT_JOB_DEFAULT_LIMIT
    ) -> SnapshotRunResult:
        """Run snapshot creation for up to `limit` subjects in the tenant.

        Paginates over subjects; for each subject runs state derivation and
        creates or replaces the snapshot. Subjects with no events are skipped
        (ValidationException). Other exceptions are counted as errors.

        Args:
            tenant_id: Tenant to run for.
            limit: Maximum number of subjects to process (default from
                SNAPSHOT_JOB_DEFAULT_LIMIT).

        Returns:
            SnapshotRunResult with counts and optional error subject ids.
        """
        snapshots_created_or_updated = 0
        skipped_no_events = 0
        error_count = 0
        error_subject_ids: list[str] = []
        total_processed = 0
        skip = 0

        while total_processed < limit:
            page_size = min(SNAPSHOT_JOB_PAGE_SIZE, limit - total_processed)
            subjects = await self._subject_repo.get_by_tenant(
                tenant_id=tenant_id,
                skip=skip,
                limit=page_size,
            )
            if not subjects:
                break

            for s in subjects:
                if total_processed >= limit:
                    break
                total_processed += 1
                try:
                    await self._create_snapshot_use_case.create_snapshot(
                        tenant_id=tenant_id,
                        subject_id=s.id,
                    )
                    snapshots_created_or_updated += 1
                except ValidationException:
                    skipped_no_events += 1
                except ResourceNotFoundException:
                    error_count += 1
                    if len(error_subject_ids) < MAX_ERROR_SUBJECT_IDS:
                        error_subject_ids.append(s.id)
                except Exception:
                    error_count += 1
                    if len(error_subject_ids) < MAX_ERROR_SUBJECT_IDS:
                        error_subject_ids.append(s.id)

            if len(subjects) < page_size:
                break
            skip += len(subjects)

        return SnapshotRunResult(
            tenant_id=tenant_id,
            subjects_processed=total_processed,
            snapshots_created_or_updated=snapshots_created_or_updated,
            skipped_no_events=skipped_no_events,
            error_count=error_count,
            error_subject_ids=tuple(error_subject_ids),
        )
