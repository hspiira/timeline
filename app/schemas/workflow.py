"""Workflow API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowAction(BaseModel):
    """Single workflow action; requires type (e.g. create_event), optional params."""

    type: str = Field(..., min_length=1, max_length=128, description="Action type")
    params: dict[str, Any] | None = None


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow."""

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
