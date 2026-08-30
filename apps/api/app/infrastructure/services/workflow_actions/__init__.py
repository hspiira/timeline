"""Workflow action handlers (OCP: add new action types without modifying the engine)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.application.interfaces.repositories import IRoleRepository, ITaskRepository
from app.application.interfaces.services import (
    IEventService,
    INotificationService,
    IWorkflowRecipientResolver,
)
from app.infrastructure.persistence.models.workflow import Workflow
from app.infrastructure.services.workflow_template_renderer import WorkflowTemplateRenderer


@dataclass
class ActionContext:
    """Dependencies and context passed to action handlers."""

    tenant_id: str
    event_service: IEventService
    notification_service: INotificationService | None
    recipient_resolver: IWorkflowRecipientResolver | None
    template_renderer: WorkflowTemplateRenderer | None
    task_repo: ITaskRepository | None
    role_repo: IRoleRepository | None


class ActionHandler(Protocol):
    """Protocol for workflow action handlers. Implement to add new action types."""

    async def execute(
        self,
        action: dict[str, Any],
        triggered_by: Any,
        workflow: Workflow,
        execution_log: list[dict[str, Any]],
        ctx: ActionContext,
    ) -> tuple[int, int]:
        """Execute the action. Append outcome to execution_log. Return (executed_inc, failed_inc)."""
        ...


def get_default_handlers() -> dict[str, ActionHandler]:
    """Return the default action type -> handler registry. Engine uses this; tests can override."""
    from app.infrastructure.services.workflow_actions.create_event import CreateEventHandler
    from app.infrastructure.services.workflow_actions.create_task import CreateTaskHandler
    from app.infrastructure.services.workflow_actions.notify import NotifyHandler

    return {
        "create_event": CreateEventHandler(),
        "notify": NotifyHandler(),
        "create_task": CreateTaskHandler(),
    }
