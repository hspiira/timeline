"""Subject API schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.value_objects.core import SubjectType


class SubjectCreateRequest(BaseModel):
    """Request body for creating a subject."""

    subject_type: str = Field(..., min_length=1, max_length=64)
    external_ref: str | None = Field(default=None, max_length=255)


class SubjectUpdate(BaseModel):
    """Request body for updating a subject (partial)."""

    external_ref: str | None = Field(default=None, max_length=255)


class SubjectResponse(BaseModel):
    """Subject response (minimal)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    subject_type: str
    external_ref: str | None

    @field_validator("subject_type", mode="before")
    @classmethod
    def _subject_type_to_str(cls, v: SubjectType | str) -> str:
        """Accept SubjectType from DTO; serialize to str for JSON."""
        return v.value if isinstance(v, SubjectType) else v
