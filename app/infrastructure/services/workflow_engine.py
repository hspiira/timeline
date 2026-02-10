"""Workflow engine: execute workflows triggered by events (implements IWorkflowEngine)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.services import IEventService
from app.infrastructure.persistence.models.workflow import (
    Workflow,
    WorkflowExecution,
)
from app.schemas.event import EventCreate
from app.shared.enums import WorkflowExecutionStatus
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class WorkflowEngine:
    """Finds and runs workflows for an event (create_event actions, etc.)."""

    def __init__(
        self,
        db: AsyncSession,
        event_service: IEventService,
    ) -> None:
        self.db = db
        self.event_service = event_service

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

    def _evaluate_conditions(self, workflow: Workflow, event: Any) -> bool:
        if not workflow.trigger_conditions:
            return True
        for key, expected_value in workflow.trigger_conditions.items():
            if key.startswith("payload."):
                field = key.replace("payload.", "")
                if getattr(event, "payload", {}).get(field) != expected_value:
                    return False
        return True

    async def _execute_workflow(
        self, workflow: Workflow, triggered_by: Any
    ) -> WorkflowExecution:
        execution = WorkflowExecution(
            tenant_id=workflow.tenant_id,
            workflow_id=workflow.id,
            triggered_by_event_id=triggered_by.id,
            triggered_by_subject_id=triggered_by.subject_id,
            status=WorkflowExecutionStatus.RUNNING.value,
            started_at=utc_now(),
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
                        event_create = EventCreate(
                            subject_id=triggered_by.subject_id,
                            event_type=params.get("event_type", ""),
                            schema_version=params.get("schema_version", 1),
                            event_time=utc_now(),
                            payload=params.get("payload", {}),
                        )
                        created = await self.event_service.create_event(
                            tenant_id=workflow.tenant_id,
                            event=event_create,
                            trigger_workflows=False,
                        )
                        execution_log.append(
                            {"action": action_type, "status": "success", "event_id": created.id}
                        )
                        actions_executed += 1
                    except Exception as e:
                        execution_log.append(
                            {"action": action_type, "status": "failed", "error": str(e)}
                        )
                        actions_failed += 1
                else:
                    execution_log.append(
                        {"action": action_type, "status": "skipped", "reason": f"Unknown: {action_type}"}
                    )
            execution.status = WorkflowExecutionStatus.COMPLETED.value
        except Exception as e:
            execution.status = WorkflowExecutionStatus.FAILED.value
            execution.error_message = str(e)

        execution.completed_at = utc_now()
        execution.actions_executed = actions_executed
        execution.actions_failed = actions_failed
        execution.execution_log = execution_log
        await self.db.flush()
        return execution
