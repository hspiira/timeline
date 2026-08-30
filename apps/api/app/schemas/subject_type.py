"""Subject type configuration API schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubjectTypeCreateRequest(BaseModel):
    """Request body for creating a subject type. Accepts 'schema' in JSON."""

    model_config = ConfigDict(populate_by_name=True)

    type_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    schema_definition: dict[str, Any] | None = Field(default=None, alias="schema")
    is_active: bool = True
    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=50)
    has_timeline: bool = True
    allow_documents: bool = True
    allowed_event_types: list[str] | None = Field(default=None)


class SubjectTypeUpdateRequest(BaseModel):
    """Request body for PATCH (partial update). Accepts 'schema' in JSON."""

    model_config = ConfigDict(populate_by_name=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    schema_definition: dict[str, Any] | None = Field(default=None, alias="schema")
    is_active: bool | None = None
    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=50)
    has_timeline: bool | None = None
    allow_documents: bool | None = None
    allowed_event_types: list[str] | None = None


class SubjectTypeListItem(BaseModel):
    """Subject type list item."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    type_name: str
    display_name: str
    description: str | None
    version: int
    is_active: bool
    icon: str | None
    color: str | None
    has_timeline: bool
    allow_documents: bool
    allowed_event_types: list[str] | None = None


class SubjectTypeResponse(BaseModel):
    """Subject type full response. Serializes as 'schema' in JSON."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    id: str
    tenant_id: str
    type_name: str
    display_name: str
    description: str | None
    schema_definition: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        validation_alias="schema",
        serialization_alias="schema",
    )
    version: int
    is_active: bool
    icon: str | None
    color: str | None
    has_timeline: bool
    allow_documents: bool
    allowed_event_types: list[str] | None = None
    created_by: str | None
