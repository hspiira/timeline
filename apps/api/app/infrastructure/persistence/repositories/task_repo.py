"""Task repository for workflow create_task action."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.task import TaskResult
from app.infrastructure.persistence.models.task import Task


def _to_result(t: Task) -> TaskResult:
    """Map Task ORM to TaskResult DTO."""
    return TaskResult(
        id=t.id,
        tenant_id=t.tenant_id,
        subject_id=t.subject_id,
        event_id=t.event_id,
        assigned_to_role_id=t.assigned_to_role_id,
        assigned_to_user_id=t.assigned_to_user_id,
        title=t.title,
        due_at=t.due_at,
        status=t.status,
        description=t.description,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


class TaskRepository:
    """Task repository. Implements ITaskRepository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        tenant_id: str,
        subject_id: str,
        event_id: str | None,
        title: str,
        *,
        assigned_to_role_id: str | None = None,
        assigned_to_user_id: str | None = None,
        due_at: datetime | None = None,
        status: str = "open",
        description: str | None = None,
    ) -> TaskResult:
        """Create a task and return the result DTO."""
        task = Task(
            tenant_id=tenant_id,
            subject_id=subject_id,
            event_id=event_id,
            title=title,
            assigned_to_role_id=assigned_to_role_id,
            assigned_to_user_id=assigned_to_user_id,
            due_at=due_at,
            status=status,
            description=description,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return _to_result(task)
