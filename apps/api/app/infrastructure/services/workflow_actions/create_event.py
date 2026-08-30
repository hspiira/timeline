"""create_event workflow action handler."""

from __future__ import annotations

from typing import Any

from app.application.dtos.event import EventCreate
from app.infrastructure.persistence.models.workflow import Workflow
from app.infrastructure.services.workflow_actions import ActionContext
from app.shared.utils.datetime import utc_now


class CreateEventHandler:
    """Handler for action type create_event."""

    async def execute(
        self,
        action: dict[str, Any],
        triggered_by: Any,
        workflow: Workflow,
        execution_log: list[dict[str, Any]],
        ctx: ActionContext,
    ) -> tuple[int, int]:
        action_type = action.get("type", "create_event")
        params = action.get("params", {})
        try:
            cmd = EventCreate(
                subject_id=triggered_by.subject_id,
                event_type=params.get("event_type", ""),
                schema_version=params.get("schema_version", 1),
                event_time=utc_now(),
                payload=params.get("payload", {}),
                workflow_instance_id=getattr(
                    triggered_by, "workflow_instance_id", None
                ),
                correlation_id=getattr(triggered_by, "correlation_id", None),
            )
            created = await ctx.event_service.create_event(
                ctx.tenant_id,
                cmd,
                trigger_workflows=False,
            )
            execution_log.append(
                {
                    "action": action_type,
                    "status": "success",
                    "event_id": created.id,
                }
            )
            return (1, 0)
        except Exception as e:
            execution_log.append(
                {"action": action_type, "status": "failed", "error": str(e)}
            )
            return (0, 1)
