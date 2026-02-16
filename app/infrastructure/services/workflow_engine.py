"""Workflow engine: execute workflows triggered by events (implements IWorkflowEngine)."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event import EventCreate
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
from app.infrastructure.services.workflow_template_renderer import WorkflowTemplateRenderer
from app.shared.enums import WorkflowExecutionStatus
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


def _advisory_lock_key(workflow_id: str, tenant_id: str, day: date) -> int:
    """Stable 63-bit key for pg_advisory_xact_lock (workflow + tenant + day)."""
    raw = hashlib.sha256(f"{workflow_id}:{tenant_id}:{day.isoformat()}".encode()).digest()[:8]
    return int.from_bytes(raw, "big") % (2**63)


async def _count_executions_today(
    db: AsyncSession,
    workflow_id: str,
    tenant_id: str,
    *,
    reference: datetime | None = None,
) -> int:
    """Count workflow executions started today (UTC). Uses reference timestamp when provided so lock key and query share the same day."""
    now = reference or utc_now()
    day_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(
        select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.tenant_id == tenant_id,
            WorkflowExecution.started_at >= day_start,
            WorkflowExecution.started_at < day_end,
        )
    )
    return result.scalar_one() or 0


class _EventLike(Protocol):
    """Minimal event shape for condition evaluation (payload only)."""

    payload: dict[str, Any]


class WorkflowEngine:
    """Finds and runs workflows for an event (create_event, notify, create_task)."""

    def __init__(
        self,
        db: AsyncSession,
        event_service: IEventService,
        workflow_repo: WorkflowRepository,
        *,
        notification_service: INotificationService | None = None,
        recipient_resolver: IWorkflowRecipientResolver | None = None,
        template_renderer: WorkflowTemplateRenderer | None = None,
        task_repo: ITaskRepository | None = None,
        role_repo: IRoleRepository | None = None,
    ) -> None:
        self.db = db
        self.event_service = event_service
        self.workflow_repo = workflow_repo
        self._notification_service = notification_service
        self._recipient_resolver = recipient_resolver
        self._template_renderer = template_renderer
        self._task_repo = task_repo
        self._role_repo = role_repo

    async def process_event_triggers(
        self, event: Any, tenant_id: str
    ) -> list[WorkflowExecution]:
        """Find matching workflows, evaluate conditions, execute and return executions."""
        workflows = await self._find_matching_workflows(
            event_type=event.event_type, tenant_id=tenant_id
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
            # Serialize rate-limit check per (workflow, tenant, day) to avoid TOCTOU.
            # Requires PostgreSQL (pg_advisory_xact_lock); held until transaction end.
            lock_key = _advisory_lock_key(
                workflow.id, workflow.tenant_id, now.date()
            )
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
            )
            count = await _count_executions_today(
                self.db, workflow.id, workflow.tenant_id, reference=now
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

        try:
            for action in workflow.actions or []:
                action_type = action.get("type")
                if action_type == "create_event":
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
                            correlation_id=getattr(
                                triggered_by, "correlation_id", None
                            ),
                        )
                        created = await self.event_service.create_event(
                            tenant_id=workflow.tenant_id,
                            data=cmd,
                            trigger_workflows=False,
                        )
                        execution_log.append(
                            {
                                "action": action_type,
                                "status": "success",
                                "event_id": created.id,
                            }
                        )
                        actions_executed += 1
                    except Exception as e:
                        execution_log.append(
                            {"action": action_type, "status": "failed", "error": str(e)}
                        )
                        actions_failed += 1
                elif action_type == "notify":
                    params = action.get("params", {})
                    role_code = params.get("role")
                    template_key = params.get("template")
                    data = params.get("data")
                    if not role_code or not template_key:
                        execution_log.append(
                            {
                                "action": action_type,
                                "status": "failed",
                                "error": "notify requires params.role and params.template",
                            }
                        )
                        actions_failed += 1
                    elif not self._recipient_resolver or not self._template_renderer or not self._notification_service:
                        execution_log.append(
                            {
                                "action": action_type,
                                "status": "skipped",
                                "reason": "notify not configured (missing resolver/templates/notification)",
                            }
                        )
                    else:
                        try:
                            emails = await self._recipient_resolver.get_emails_for_role(
                                workflow.tenant_id, role_code
                            )
                            if not emails:
                                logger.warning(
                                    "notify action skipped: no recipients for role %r (tenant_id=%s)",
                                    role_code,
                                    workflow.tenant_id,
                                )
                                execution_log.append(
                                    {
                                        "action": action_type,
                                        "status": "skipped",
                                        "reason": f"no recipients found for role '{role_code}'",
                                    }
                                )
                                continue
                            payload = getattr(triggered_by, "payload", None) or {}
                            subject, body = self._template_renderer.render(
                                template_key, triggered_by, payload, data
                            )
                            await self._notification_service.send(emails, subject, body)
                            execution_log.append(
                                {
                                    "action": action_type,
                                    "status": "success",
                                    "recipients_count": len(emails),
                                }
                            )
                            actions_executed += 1
                        except KeyError as e:
                            execution_log.append(
                                {"action": action_type, "status": "failed", "error": str(e)}
                            )
                            actions_failed += 1
                        except Exception as e:
                            execution_log.append(
                                {"action": action_type, "status": "failed", "error": str(e)}
                            )
                            actions_failed += 1
                elif action_type == "create_task":
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
                        actions_failed += 1
                    elif not self._task_repo:
                        execution_log.append(
                            {
                                "action": action_type,
                                "status": "skipped",
                                "reason": "task repository not configured",
                            }
                        )
                    else:
                        try:
                            assigned_to_role_id: str | None = None
                            if assigned_to_role_code and self._role_repo:
                                role_result = await self._role_repo.get_by_code_and_tenant(
                                    assigned_to_role_code, workflow.tenant_id
                                )
                                if role_result:
                                    assigned_to_role_id = role_result.id
                            due_at_dt: datetime | None = None
                            if due_at_str:
                                due_at_dt = datetime.fromisoformat(
                                    due_at_str.replace("Z", "+00:00")
                                )
                            task = await self._task_repo.create(
                                tenant_id=workflow.tenant_id,
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
                            actions_executed += 1
                        except Exception as e:
                            execution_log.append(
                                {"action": action_type, "status": "failed", "error": str(e)}
                            )
                            actions_failed += 1
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
