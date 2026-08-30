"""Document requirement API schemas."""

from pydantic import BaseModel, ConfigDict, Field


class DocumentRequirementCreateRequest(BaseModel):
    """Request body for creating a document requirement."""

    document_category_id: str = Field(..., min_length=1)
    min_count: int = Field(1, ge=1)


class DocumentRequirementResponse(BaseModel):
    """Document requirement response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workflow_id: str
    step_definition_id: str | None
    document_category_id: str
    min_count: int
