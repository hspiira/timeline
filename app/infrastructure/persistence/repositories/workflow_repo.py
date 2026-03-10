"""Workflow and WorkflowExecution repository."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.workflow import Workflow, WorkflowExecution
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction
from app.shared.utils.datetime import utc_now

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
        *,
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

    async def acquire_daily_rate_limit_lock(
        self, workflow_id: str, tenant_id: str, day: date
    ) -> None:
        """Acquire PostgreSQL advisory lock for (workflow, tenant, day). Held until transaction end.

        Serializes rate-limit checks per (workflow_id, tenant_id, day) to avoid TOCTOU.
        Call before counting executions for the day when max_executions_per_day is set.
        """
        import hashlib

        raw = hashlib.sha256(
            f"{workflow_id}:{tenant_id}:{day.isoformat()}".encode()
        ).digest()[:8]
        lock_key = int.from_bytes(raw, "big") % (2**63)
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
        )

    async def count_executions_today(
        self,
        workflow_id: str,
        tenant_id: str,
        *,
        reference: datetime | None = None,
    ) -> int:
        """Count workflow executions started today (UTC). reference aligns day with lock."""
        from app.shared.utils.datetime import utc_now

        now = reference or utc_now()
        day_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        result = await self.db.execute(
            select(func.count(WorkflowExecution.id)).where(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.tenant_id == tenant_id,
                WorkflowExecution.started_at >= day_start,
                WorkflowExecution.started_at < day_end,
            )
        )
        return result.scalar_one() or 0

    async def create_workflow(
        self,
        tenant_id: str,
        name: str,
        trigger_event_type: str,
        actions: list[dict[str, Any]],
        *,
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

    async def soft_delete(self, workflow_id: str, tenant_id: str) -> Workflow | None:
        """Soft-delete workflow (set deleted_at). Returns updated workflow or None."""
        workflow = await self.get_by_id_and_tenant(workflow_id, tenant_id)
        if not workflow:
            return None
        workflow.deleted_at = utc_now()
        updated = await self.update_without_audit(workflow)
        await self.emit_custom_audit(updated, AuditAction.DELETED)
        return updated


class WorkflowExecutionRepository:
    """Repository for WorkflowExecution (read-only for API)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(
        self, execution_id: str, tenant_id: str
    ) -> WorkflowExecution | None:
        result = await self.db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_workflow(
        self,
        workflow_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        result = await self.db.execute(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
            .order_by(WorkflowExecution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
