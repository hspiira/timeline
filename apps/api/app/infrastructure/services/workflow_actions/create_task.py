"""create_task workflow action handler."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.infrastructure.persistence.models.workflow import Workflow
from app.infrastructure.services.workflow_actions import ActionContext


class CreateTaskHandler:
    """Handler for action type create_task."""

    async def execute(
        self,
        action: dict[str, Any],
        triggered_by: Any,
        workflow: Workflow,
        execution_log: list[dict[str, Any]],
        ctx: ActionContext,
    ) -> tuple[int, int]:
        action_type = action.get("type", "create_task")
        params = action.get("params", {})
        title = params.get("title") or ""
        assigned_to_role_code = params.get("assigned_to_role")
        assigned_to_user_id = params.get("assigned_to_user_id")
        due_at_str = params.get("due_at")
        if not title:
            execution_log.append(
                {
                    "action": action_type,
                    "status": "failed",
                    "error": "create_task requires params.title",
                }
            )
            return (0, 1)
        if not ctx.task_repo:
            execution_log.append(
                {
                    "action": action_type,
                    "status": "skipped",
                    "reason": "task repository not configured",
                }
            )
            return (0, 0)
        try:
            assigned_to_role_id: str | None = None
            if assigned_to_role_code and ctx.role_repo:
                role_result = await ctx.role_repo.get_by_code_and_tenant(
                    assigned_to_role_code, ctx.tenant_id
                )
                if role_result:
                    assigned_to_role_id = role_result.id
            due_at_dt: datetime | None = None
            if due_at_str:
                due_at_dt = datetime.fromisoformat(
                    due_at_str.replace("Z", "+00:00")
                )
            task = await ctx.task_repo.create(
                tenant_id=ctx.tenant_id,
                subject_id=triggered_by.subject_id,
                event_id=getattr(triggered_by, "id", None),
                title=title,
                assigned_to_role_id=assigned_to_role_id,
                assigned_to_user_id=assigned_to_user_id,
                due_at=due_at_dt,
            )
            execution_log.append(
                {
                    "action": action_type,
                    "status": "success",
                    "task_id": task.id,
                }
            )
            return (1, 0)
        except Exception as e:
            execution_log.append(
                {"action": action_type, "status": "failed", "error": str(e)}
            )
            return (0, 1)
