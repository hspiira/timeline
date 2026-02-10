"""Subject API schemas."""

from pydantic import BaseModel, Field


class SubjectCreateRequest(BaseModel):
    """Request body for creating a subject."""

    subject_type: str = Field(..., min_length=1, max_length=64)
    external_ref: str | None = Field(default=None, max_length=255)


class SubjectResponse(BaseModel):
    """Subject response (minimal)."""

    id: str
    tenant_id: str
    subject_type: str
    external_ref: str | None
