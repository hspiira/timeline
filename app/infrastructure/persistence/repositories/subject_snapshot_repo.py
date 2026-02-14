"""Subject snapshot repository. One snapshot per subject (checkpoint for state derivation)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.subject_snapshot import SubjectSnapshotResult
from app.infrastructure.persistence.models.subject_snapshot import SubjectSnapshot
from app.infrastructure.persistence.repositories.base import BaseRepository


def _to_result(s: SubjectSnapshot) -> SubjectSnapshotResult:
    """Map ORM to DTO."""
    return SubjectSnapshotResult(
        id=s.id,
        subject_id=s.subject_id,
        tenant_id=s.tenant_id,
        snapshot_at_event_id=s.snapshot_at_event_id,
        state_json=s.state_json,
        event_count_at_snapshot=s.event_count_at_snapshot,
        created_at=s.created_at,
    )


class SubjectSnapshotRepository(BaseRepository[SubjectSnapshot]):
    """Subject snapshot repository. get_latest_by_subject; create_snapshot (replace if exists)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, SubjectSnapshot)

    async def get_latest_by_subject(
        self, subject_id: str, tenant_id: str
    ) -> SubjectSnapshotResult | None:
        """Return latest snapshot for subject in tenant, or None."""
        result = await self.db.execute(
            select(SubjectSnapshot)
            .where(
                SubjectSnapshot.subject_id == subject_id,
                SubjectSnapshot.tenant_id == tenant_id,
            )
            .order_by(SubjectSnapshot.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def create_snapshot(
        self,
        subject_id: str,
        tenant_id: str,
        snapshot_at_event_id: str,
        state_json: dict,
        event_count_at_snapshot: int = 0,
    ) -> SubjectSnapshotResult:
        """Create or replace snapshot for subject (one per subject)."""
        existing = await self.db.execute(
            select(SubjectSnapshot).where(
                SubjectSnapshot.subject_id == subject_id,
                SubjectSnapshot.tenant_id == tenant_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.snapshot_at_event_id = snapshot_at_event_id
            row.state_json = state_json
            row.event_count_at_snapshot = event_count_at_snapshot
            await self.db.flush()
            await self.db.refresh(row)
            return _to_result(row)
        snapshot = SubjectSnapshot(
            subject_id=subject_id,
            tenant_id=tenant_id,
            snapshot_at_event_id=snapshot_at_event_id,
            state_json=state_json,
            event_count_at_snapshot=event_count_at_snapshot,
        )
        created = await self.create(snapshot)
        return _to_result(created)
