"""Projection repository: definition and state (Phase 5)."""

from __future__ import annotations

from sqlalchemy import Float, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.dtos.projection import (
    ProjectionDefinitionResult,
    ProjectionStateResult,
)
from app.infrastructure.persistence.models.projection import (
    ProjectionDefinition,
    ProjectionState,
)
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.shared.utils.generators import generate_cuid


def _definition_to_result(d: ProjectionDefinition) -> ProjectionDefinitionResult:
    """Map ORM ProjectionDefinition to ProjectionDefinitionResult."""
    return ProjectionDefinitionResult(
        id=d.id,
        tenant_id=d.tenant_id,
        name=d.name,
        version=d.version,
        subject_type=d.subject_type,
        last_event_seq=d.last_event_seq,
        active=d.active,
        created_at=d.created_at,
    )


def _state_to_result(s: ProjectionState) -> ProjectionStateResult:
    """Map ORM ProjectionState to ProjectionStateResult."""
    return ProjectionStateResult(
        id=s.id,
        projection_id=s.projection_id,
        subject_id=s.subject_id,
        state=dict(s.state) if s.state else {},
        updated_at=s.updated_at,
    )


class ProjectionRepository(BaseRepository[ProjectionDefinition]):
    """Projection definition and state repository."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ProjectionDefinition)

    async def list_active(
        self, tenant_id: str | None = None
    ) -> list[ProjectionDefinitionResult]:
        """All active projection definitions, optionally filtered by tenant."""
        q = select(ProjectionDefinition).where(ProjectionDefinition.active.is_(True))
        if tenant_id is not None:
            q = q.where(ProjectionDefinition.tenant_id == tenant_id)
        result = await self.db.execute(q)
        rows = result.scalars().all()
        return [_definition_to_result(r) for r in rows]

    async def list_by_tenant(
        self, tenant_id: str
    ) -> list[ProjectionDefinitionResult]:
        """All projection definitions for tenant (active and inactive)."""
        result = await self.db.execute(
            select(ProjectionDefinition).where(
                ProjectionDefinition.tenant_id == tenant_id
            )
        )
        rows = result.scalars().all()
        return [_definition_to_result(r) for r in rows]

    async def get_by_name_version(
        self, tenant_id: str, name: str, version: int
    ) -> ProjectionDefinitionResult | None:
        """Return projection definition by tenant, name and version."""
        result = await self.db.execute(
            select(ProjectionDefinition).where(
                ProjectionDefinition.tenant_id == tenant_id,
                ProjectionDefinition.name == name,
                ProjectionDefinition.version == version,
            )
        )
        row = result.scalar_one_or_none()
        return _definition_to_result(row) if row else None

    async def create(
        self,
        tenant_id: str,
        name: str,
        version: int,
        subject_type: str | None,
    ) -> ProjectionDefinitionResult:
        """Create projection definition with last_event_seq=0."""
        obj = ProjectionDefinition(
            id=generate_cuid(),
            tenant_id=tenant_id,
            name=name,
            version=version,
            subject_type=subject_type,
            last_event_seq=0,
            active=True,
        )
        created = await super().create(obj)
        return _definition_to_result(created)

    async def advance_watermark(self, projection_id: str, new_seq: int) -> None:
        """Update last_event_seq for the projection definition."""
        await self.db.execute(
            update(ProjectionDefinition)
            .where(ProjectionDefinition.id == projection_id)
            .values(last_event_seq=new_seq)
        )
        await self.db.flush()

    async def get_state(
        self, projection_id: str, subject_id: str
    ) -> ProjectionStateResult | None:
        """Return projection state for (projection_id, subject_id), or None."""
        result = await self.db.execute(
            select(ProjectionState).where(
                ProjectionState.projection_id == projection_id,
                ProjectionState.subject_id == subject_id,
            )
        )
        row = result.scalar_one_or_none()
        return _state_to_result(row) if row else None

    async def upsert_state(
        self, projection_id: str, subject_id: str, state: dict
    ) -> None:
        """Insert or update projection state for (projection_id, subject_id)."""
        result = await self.db.execute(
            select(ProjectionState).where(
                ProjectionState.projection_id == projection_id,
                ProjectionState.subject_id == subject_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.state = state
            await self.db.flush()
            await self.db.refresh(row)
        else:
            new_id = generate_cuid()
            obj = ProjectionState(
                id=new_id,
                projection_id=projection_id,
                subject_id=subject_id,
                state=state,
            )
            self.db.add(obj)
            await self.db.flush()

    async def list_states(
        self, projection_id: str, skip: int = 0, limit: int = 100
    ) -> list[ProjectionStateResult]:
        """List projection states for projection (paginated)."""
        result = await self.db.execute(
            select(ProjectionState)
            .where(ProjectionState.projection_id == projection_id)
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [_state_to_result(r) for r in rows]

    async def lock_for_advance(
        self, projection_id: str
    ) -> ProjectionDefinitionResult | None:
        """SELECT ... FOR UPDATE SKIP LOCKED on the definition row. Returns None if locked by another worker."""
        result = await self.db.execute(
            select(ProjectionDefinition)
            .where(ProjectionDefinition.id == projection_id)
            .with_for_update(skip_locked=True)
        )
        row = result.scalar_one_or_none()
        return _definition_to_result(row) if row else None

    async def deactivate(
        self, tenant_id: str, name: str, version: int
    ) -> None:
        """Set active=False for the projection definition."""
        await self.db.execute(
            update(ProjectionDefinition).where(
                ProjectionDefinition.tenant_id == tenant_id,
                ProjectionDefinition.name == name,
                ProjectionDefinition.version == version,
            ).values(active=False)
        )
        await self.db.flush()

    async def reset_watermark(
        self, tenant_id: str, name: str, version: int
    ) -> None:
        """Set last_event_seq=0 for the projection (full replay on next cycle)."""
        await self.db.execute(
            update(ProjectionDefinition).where(
                ProjectionDefinition.tenant_id == tenant_id,
                ProjectionDefinition.name == name,
                ProjectionDefinition.version == version,
            ).values(last_event_seq=0)
        )
        await self.db.flush()

    async def count_states(self, projection_id: str) -> int:
        """Return count of projection_state rows for this projection."""
        result = await self.db.execute(
            select(func.count(ProjectionState.id)).where(
                ProjectionState.projection_id == projection_id
            )
        )
        return result.scalar() or 0

    async def get_top_by_field(
        self,
        projection_id: str,
        field: str,
        limit: int = 10,
    ) -> list[ProjectionStateResult]:
        """Return top N states ordered by state->>field as numeric DESC."""
        q = (
            select(ProjectionState)
            .where(ProjectionState.projection_id == projection_id)
            .order_by(
                cast(
                    ProjectionState.state[field].astext,
                    Float,
                ).desc().nulls_last()
            )
            .limit(limit)
        )
        result = await self.db.execute(q)
        rows = result.scalars().all()
        return [_state_to_result(r) for r in rows]
