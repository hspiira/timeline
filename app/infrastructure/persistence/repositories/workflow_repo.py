"""Workflow and WorkflowExecution repository."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.workflow import Workflow
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class WorkflowRepository(AuditableRepository[Workflow]):
    """Workflow repository."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Workflow, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "workflow"

    def _get_tenant_id(self, obj: Workflow) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: Workflow) -> dict[str, Any]:
        return {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description,
            "trigger_event_type": obj.trigger_event_type,
            "is_active": obj.is_active,
            "execution_order": obj.execution_order,
        }

    async def get_by_id_and_tenant(
        self, workflow_id: str, tenant_id: str
    ) -> Workflow | None:
        result = await self.db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id,
                Workflow.tenant_id == tenant_id,
                Workflow.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Workflow]:
        q = select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.deleted_at.is_(None),
        )
        if not include_inactive:
            q = q.where(Workflow.is_active.is_(True))
        q = q.order_by(Workflow.execution_order.asc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_trigger(self, tenant_id: str, event_type: str) -> list[Workflow]:
        result = await self.db.execute(
            select(Workflow)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.trigger_event_type == event_type,
                Workflow.is_active.is_(True),
                Workflow.deleted_at.is_(None),
            )
            .order_by(Workflow.execution_order.asc())
        )
        return list(result.scalars().all())

    async def create_workflow(
        self,
        tenant_id: str,
        name: str,
        trigger_event_type: str,
        actions: list[dict[str, Any]],
        description: str | None = None,
        is_active: bool = True,
        trigger_conditions: dict[str, Any] | None = None,
        max_executions_per_day: int | None = None,
        execution_order: int = 0,
    ) -> Workflow:
        """Create workflow; return created entity."""
        workflow = Workflow(
            tenant_id=tenant_id,
            name=name,
            description=description,
            is_active=is_active,
            trigger_event_type=trigger_event_type,
            trigger_conditions=trigger_conditions,
            actions=actions,
            max_executions_per_day=max_executions_per_day,
            execution_order=execution_order,
        )
        return await self.create(workflow)
