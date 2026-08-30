"""DTOs for workflow-created tasks (no dependency on ORM)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TaskResult:
    """Task created by workflow create_task action."""

    id: str
    tenant_id: str
    subject_id: str
    event_id: str | None
    assigned_to_role_id: str | None
    assigned_to_user_id: str | None
    title: str
    due_at: datetime | None
    status: str
    description: str | None
    created_at: datetime
    updated_at: datetime
