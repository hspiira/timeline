"""Flow API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlowCreateRequest(BaseModel):
    """Request body for creating a flow."""

    name: str = Field(..., min_length=1, max_length=500)
    workflow_id: str | None = None
    hierarchy_values: dict[str, str] | None = None
    subject_ids: list[str] | None = None
    subject_roles: dict[str, str] | None = None  # subject_id -> role


class FlowUpdateRequest(BaseModel):
    """Request body for updating a flow (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=500)
    hierarchy_values: dict[str, str] | None = None


class FlowResponse(BaseModel):
    """Flow response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    workflow_id: str | None
    created_at: datetime
    updated_at: datetime
    hierarchy_values: dict[str, str] | None


class FlowSubjectResponse(BaseModel):
    """Flow-subject link response."""

    flow_id: str
    subject_id: str
    role: str | None


class FlowAddSubjectsRequest(BaseModel):
    """Request body for adding subjects to a flow."""

    subject_ids: list[str] = Field(..., min_length=1)
    roles: dict[str, str] | None = None  # subject_id -> role


class DocumentComplianceItemResponse(BaseModel):
    """Required vs present for one document category in a flow."""

    document_category_id: str
    category_name: str
    display_name: str
    required_count: int
    present_count: int
    satisfied: bool
    blocked_reason: str | None


class FlowDocumentComplianceResponse(BaseModel):
    """Document compliance check result for a flow."""

    flow_id: str
    items: list[DocumentComplianceItemResponse]
    all_satisfied: bool
    blocked_reasons: list[str]
