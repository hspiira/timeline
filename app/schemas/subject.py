"""Subject API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.value_objects.core import SubjectType


class SubjectCreateRequest(BaseModel):
    """Request body for creating a subject."""

    subject_type: str = Field(..., min_length=1, max_length=64)
    external_ref: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=500)
    attributes: dict[str, Any] | None = Field(default=None)


class SubjectUpdate(BaseModel):
    """Request body for updating a subject (partial)."""

    external_ref: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=500)
    attributes: dict[str, Any] | None = Field(default=None)


class SubjectResponse(BaseModel):
    """Subject response (minimal)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    subject_type: str
    external_ref: str | None
    display_name: str | None = None
    attributes: dict[str, Any] | None = None

    @field_validator("subject_type", mode="before")
    @classmethod
    def _subject_type_to_str(cls, v: SubjectType | str) -> str:
        """Accept SubjectType from DTO; serialize to str for JSON."""
        return v.value if isinstance(v, SubjectType) else v


class SubjectErasureRequest(BaseModel):
    """Request body for subject data erasure (GDPR)."""

    strategy: str = Field(
        default="anonymize",
        description="anonymize (redact PII) or delete (remove subject and documents)",
    )


class SubjectStateResponse(BaseModel):
    """Derived state from event replay (get_current_state)."""

    state: dict[str, Any]
    last_event_id: str | None
    event_count: int


class SubjectSnapshotResponse(BaseModel):
    """Created or updated subject snapshot (on-demand checkpoint)."""

    id: str
    subject_id: str
    snapshot_at_event_id: str
    event_count_at_snapshot: int
    created_at: datetime
