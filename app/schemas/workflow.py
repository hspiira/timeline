"""Workflow API schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=255)
    trigger_event_type: str = Field(..., min_length=1, max_length=128)
    actions: list[dict[str, Any]] = Field(...)
    description: str | None = None
    is_active: bool = True
    trigger_conditions: dict[str, Any] | None = None
    max_executions_per_day: int | None = None
    execution_order: int = 0


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
