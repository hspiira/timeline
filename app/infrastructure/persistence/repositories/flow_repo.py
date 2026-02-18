"""Flow and FlowSubject repository. Returns application DTOs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.flow import FlowResult, FlowSubjectResult
from app.domain.exceptions import ResourceNotFoundException, ValidationException
from app.infrastructure.persistence.models.flow import Flow, FlowSubject
from app.infrastructure.persistence.models.subject import Subject
from app.infrastructure.persistence.repositories.base import BaseRepository


def _flow_to_result(f: Flow) -> FlowResult:
    """Map Flow ORM to FlowResult."""
    return FlowResult(
        id=f.id,
        tenant_id=f.tenant_id,
        name=f.name,
        workflow_id=f.workflow_id,
        created_at=f.created_at,
        updated_at=f.updated_at,
        hierarchy_values=f.hierarchy_values,
    )


class FlowRepository(BaseRepository[Flow]):
    """Flow repository. All access tenant-scoped via parameters."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Flow)

    async def get_by_id(self, flow_id: str, tenant_id: str) -> FlowResult | None:
        """Return flow by ID if it belongs to tenant."""
        result = await self.db.execute(
            select(Flow).where(
                Flow.id == flow_id,
                Flow.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _flow_to_result(row) if row else None

    async def get_entity_by_id_and_tenant(
        self, flow_id: str, tenant_id: str
    ) -> Flow | None:
        """Return Flow ORM for write operations."""
        result = await self.db.execute(
            select(Flow).where(
                Flow.id == flow_id,
                Flow.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        workflow_id: str | None = None,
    ) -> list[FlowResult]:
        """Return flows for tenant with optional workflow filter."""
        q = select(Flow).where(Flow.tenant_id == tenant_id).order_by(Flow.created_at.desc())
        if workflow_id is not None:
            q = q.where(Flow.workflow_id == workflow_id)
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return [_flow_to_result(f) for f in result.scalars().all()]

    async def create_flow(
        self,
        tenant_id: str,
        name: str,
        *,
        workflow_id: str | None = None,
        hierarchy_values: dict[str, str] | None = None,
        subject_ids: list[str] | None = None,
        subject_roles: dict[str, str] | None = None,
    ) -> FlowResult:
        """Create a flow and optionally link subjects. Subjects must belong to tenant."""
        flow = Flow(
            tenant_id=tenant_id,
            name=name,
            workflow_id=workflow_id,
            hierarchy_values=hierarchy_values,
        )
        flow = await self.create(flow)
        if subject_ids:
            subject_roles = subject_roles or {}
            for sid in subject_ids:
                role = subject_roles.get(sid)
                link = FlowSubject(flow_id=flow.id, subject_id=sid, role=role)
                self.db.add(link)
            await self.db.flush()
        return _flow_to_result(flow)

    async def update_flow(
        self,
        flow_id: str,
        tenant_id: str,
        *,
        name: str | None = None,
        hierarchy_values: dict[str, str] | None = None,
    ) -> FlowResult | None:
        """Update flow; return updated result or None if not found."""
        flow = await self.get_entity_by_id_and_tenant(flow_id, tenant_id)
        if not flow:
            return None
        if name is not None:
            flow.name = name
        if hierarchy_values is not None:
            flow.hierarchy_values = hierarchy_values
        await self.update(flow)
        return _flow_to_result(flow)

    async def list_subjects_for_flow(
        self, flow_id: str, tenant_id: str
    ) -> list[FlowSubjectResult]:
        """Return flow-subject links for the flow (tenant-checked)."""
        flow = await self.get_entity_by_id_and_tenant(flow_id, tenant_id)
        if not flow:
            return []
        result = await self.db.execute(
            select(FlowSubject).where(FlowSubject.flow_id == flow_id)
        )
        return [
            FlowSubjectResult(flow_id=fs.flow_id, subject_id=fs.subject_id, role=fs.role)
            for fs in result.scalars().all()
        ]

    async def add_subjects_to_flow(
        self,
        flow_id: str,
        tenant_id: str,
        subject_ids: list[str],
        roles: dict[str, str] | None = None,
    ) -> None:
        """Link subjects to flow. Subjects must exist and belong to tenant."""
        flow = await self.get_entity_by_id_and_tenant(flow_id, tenant_id)
        if not flow:
            raise ResourceNotFoundException("flow", flow_id)
        roles = roles or {}
        for sid in subject_ids:
            sub = await self.db.get(Subject, sid)
            if not sub or sub.tenant_id != tenant_id:
                raise ValidationException(
                    f"Subject {sid} not found or does not belong to tenant",
                    field="subject_id",
                )
            existing = await self.db.execute(
                select(FlowSubject).where(
                    FlowSubject.flow_id == flow_id, FlowSubject.subject_id == sid
                )
            )
            if existing.scalar_one_or_none():
                continue
            link = FlowSubject(
                flow_id=flow_id, subject_id=sid, role=roles.get(sid)
            )
            self.db.add(link)
        await self.db.flush()

    async def remove_subject_from_flow(
        self, flow_id: str, subject_id: str, tenant_id: str
    ) -> bool:
        """Remove subject from flow; return True if removed."""
        flow = await self.get_entity_by_id_and_tenant(flow_id, tenant_id)
        if not flow:
            return False
        result = await self.db.execute(
            select(FlowSubject).where(
                FlowSubject.flow_id == flow_id, FlowSubject.subject_id == subject_id
            )
        )
        fs = result.scalar_one_or_none()
        if not fs:
            return False
        await self.db.delete(fs)
        await self.db.flush()
        return True
