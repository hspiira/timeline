"""Workflow engine: execute workflows triggered by events (implements IWorkflowEngine)."""

from __future__ import annotations

from typing import Any, Protocol

from app.application.interfaces.repositories import (
    IRoleRepository,
    ITaskRepository,
)
from app.application.interfaces.services import (
    IEventService,
    INotificationService,
    IWorkflowRecipientResolver,
)
from app.infrastructure.persistence.models.workflow import Workflow, WorkflowExecution
from app.infrastructure.persistence.repositories.workflow_repo import WorkflowRepository
from app.infrastructure.services.workflow_actions import (
    ActionContext,
    get_default_handlers,
)
from app.infrastructure.services.workflow_template_renderer import WorkflowTemplateRenderer
from app.shared.enums import WorkflowExecutionStatus
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class _EventLike(Protocol):
    """Minimal event shape for condition evaluation (payload only)."""

    payload: dict[str, Any]


class WorkflowEngine:
    """Finds and runs workflows for an event. Action types are handled by registered handlers (OCP)."""

    def __init__(
        self,
        db: Any,
        event_service: IEventService,
        workflow_repo: WorkflowRepository,
        *,
        notification_service: INotificationService | None = None,
        recipient_resolver: IWorkflowRecipientResolver | None = None,
        template_renderer: WorkflowTemplateRenderer | None = None,
        task_repo: ITaskRepository | None = None,
        role_repo: IRoleRepository | None = None,
        handlers: dict[str, Any] | None = None,
    ) -> None:
        self.db = db
        self.event_service = event_service
        self.workflow_repo = workflow_repo
        self._notification_service = notification_service
        self._recipient_resolver = recipient_resolver
        self._template_renderer = template_renderer
        self._task_repo = task_repo
        self._role_repo = role_repo
        self._handlers = handlers if handlers is not None else get_default_handlers()

    async def process_event_triggers(
        self, event: Any, tenant_id: str
    ) -> list[WorkflowExecution]:
        """Find matching workflows, evaluate conditions, execute and return executions."""
        event_type = getattr(event.event_type, "value", event.event_type)
        workflows = await self._find_matching_workflows(
            event_type=event_type, tenant_id=tenant_id
        )
        executions: list[WorkflowExecution] = []
        for workflow in workflows:
            if not self._evaluate_conditions(workflow, event):
                continue
            execution = await self._execute_workflow(workflow, event)
            executions.append(execution)
        return executions

    async def _find_matching_workflows(
        self, event_type: str, tenant_id: str
    ) -> list[Workflow]:
        return await self.workflow_repo.get_by_trigger(tenant_id, event_type)

    def _evaluate_conditions(
        self, workflow: Workflow, event: _EventLike
    ) -> bool:
        if not workflow.trigger_conditions:
            return True
        for key, expected_value in workflow.trigger_conditions.items():
            if key.startswith("payload."):
                field = key.replace("payload.", "")
                payload = getattr(event, "payload", None) or {}
                if payload.get(field) != expected_value:
                    return False
            else:
                logger.warning(
                    "Unknown trigger condition key '%s' in workflow %s — failing closed",
                    key,
                    workflow.id,
                )
                return False
        return True

    async def _execute_workflow(
        self, workflow: Workflow, triggered_by: Any
    ) -> WorkflowExecution:
        now = utc_now()
        if workflow.max_executions_per_day is not None:
            await self.workflow_repo.acquire_daily_rate_limit_lock(
                workflow.id, workflow.tenant_id, now.date()
            )
            count = await self.workflow_repo.count_executions_today(
                workflow.id, workflow.tenant_id, reference=now
            )
            if count >= workflow.max_executions_per_day:
                execution = WorkflowExecution(
                    tenant_id=workflow.tenant_id,
                    workflow_id=workflow.id,
                    triggered_by_event_id=triggered_by.id,
                    triggered_by_subject_id=triggered_by.subject_id,
                    status=WorkflowExecutionStatus.FAILED.value,
                    started_at=now,
                    completed_at=now,
                    actions_executed=0,
                    actions_failed=0,
                    execution_log=[],
                    error_message=(
                        f"Rate limit exceeded: max_executions_per_day "
                        f"({workflow.max_executions_per_day}) reached for today"
                    ),
                )
                self.db.add(execution)
                await self.db.flush()
                return execution

        execution = WorkflowExecution(
            tenant_id=workflow.tenant_id,
            workflow_id=workflow.id,
            triggered_by_event_id=triggered_by.id,
            triggered_by_subject_id=triggered_by.subject_id,
            status=WorkflowExecutionStatus.RUNNING.value,
            started_at=now,
        )
        self.db.add(execution)
        await self.db.flush()

        execution_log: list[dict[str, Any]] = []
        actions_executed = 0
        actions_failed = 0
        ctx = ActionContext(
            tenant_id=workflow.tenant_id,
            event_service=self.event_service,
            notification_service=self._notification_service,
            recipient_resolver=self._recipient_resolver,
            template_renderer=self._template_renderer,
            task_repo=self._task_repo,
            role_repo=self._role_repo,
        )

        try:
            for action in workflow.actions or []:
                action_type = action.get("type")
                handler = self._handlers.get(action_type)
                if handler:
                    executed_inc, failed_inc = await handler.execute(
                        action, triggered_by, workflow, execution_log, ctx
                    )
                    actions_executed += executed_inc
                    actions_failed += failed_inc
                else:
                    execution_log.append(
                        {
                            "action": action_type,
                            "status": "skipped",
                            "reason": f"Unknown: {action_type}",
                        }
                    )
            execution.status = WorkflowExecutionStatus.COMPLETED.value
        except Exception as e:
            logger.exception(
                "Workflow %s execution failed (tenant_id=%s, triggered_by_event_id=%s)",
                workflow.id,
                workflow.tenant_id,
                getattr(triggered_by, "id", None),
            )
            execution.status = WorkflowExecutionStatus.FAILED.value
            execution.error_message = str(e)

        execution.completed_at = utc_now()
        execution.actions_executed = actions_executed
        execution.actions_failed = actions_failed
        execution.execution_log = execution_log
        await self.db.flush()
        return execution
