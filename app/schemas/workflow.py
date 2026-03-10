"""Workflow API schemas.

Actions are validated at creation time via a discriminated union so malformed
actions (e.g. create_task without title) fail when the workflow is saved.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Action params (validated at workflow create/update)
# ---------------------------------------------------------------------------

class CreateEventParams(BaseModel):
    """Params for create_event action."""

    event_type: str = Field(..., min_length=1, max_length=128)
    schema_version: int = Field(1, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class NotifyParams(BaseModel):
    """Params for notify action. role and template are required."""

    role: str = Field(..., min_length=1, max_length=128)
    template: str = Field(..., min_length=1, max_length=256)
    data: dict[str, Any] | None = None


class CreateTaskParams(BaseModel):
    """Params for create_task action. title is required."""

    title: str = Field(..., min_length=1, max_length=512)
    assigned_to_role: str | None = Field(default=None, max_length=128)
    assigned_to_user_id: str | None = Field(default=None, max_length=128)
    due_at: str | None = Field(default=None, max_length=64)


# ---------------------------------------------------------------------------
# Discriminated action union (type + params validated at parse time)
# ---------------------------------------------------------------------------

class CreateEventAction(BaseModel):
    """Action: create a follow-up event."""

    type: Literal["create_event"] = "create_event"
    params: CreateEventParams = Field(default_factory=CreateEventParams)


class NotifyAction(BaseModel):
    """Action: send notification to a role."""

    type: Literal["notify"] = "notify"
    params: NotifyParams


class CreateTaskAction(BaseModel):
    """Action: create a task."""

    type: Literal["create_task"] = "create_task"
    params: CreateTaskParams


WorkflowAction = Annotated[
    CreateEventAction | NotifyAction | CreateTaskAction,
    Field(discriminator="type"),
]


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow. Actions validated at parse time."""

    name: str = Field(..., min_length=1, max_length=255)
    trigger_event_type: str = Field(..., min_length=1, max_length=128)
    actions: list[WorkflowAction] = Field(..., min_length=1)
    description: str | None = None
    is_active: bool = True
    trigger_conditions: dict[str, Any] | None = None
    max_executions_per_day: int | None = Field(default=None, gt=0)
    execution_order: int = 0


class WorkflowUpdate(BaseModel):
    """Request body for updating a workflow (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    trigger_conditions: dict[str, Any] | None = None
    max_executions_per_day: int | None = Field(default=None, gt=0)
    execution_order: int | None = None


class WorkflowResponse(BaseModel):
    """Workflow response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    description: str | None
    is_active: bool
    trigger_event_type: str
    trigger_conditions: dict[str, Any] | None
    actions: list[dict[str, Any]]
    max_executions_per_day: int | None
    execution_order: int


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workflow_id: str
    triggered_by_event_id: str | None
    triggered_by_subject_id: str | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    actions_executed: int
    actions_failed: int
    error_message: str | None
