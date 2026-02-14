"""Event schema (payload validation) API schemas."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.value_objects.core import EventType


class EventSchemaCreateRequest(BaseModel):
    """Request body for creating an event schema version.

    created_by is set server-side from the authenticated user; not accepted from the client.
    """

    event_type: str = Field(..., min_length=1, max_length=128)
    schema_definition: dict[str, Any] = Field(...)
    is_active: bool = True


class EventSchemaListItem(BaseModel):
    """Event schema list item (no schema_definition)."""

    id: str
    tenant_id: str
    event_type: str
    version: int
    is_active: bool
    created_by: str | None

    @field_validator("event_type", mode="before")
    @classmethod
    def _event_type_to_str(cls, v: EventType | str) -> str:
        """Accept EventType from DTO; serialize to str for JSON."""
        return v.value if isinstance(v, EventType) else v


class EventSchemaUpdate(BaseModel):
    """Request body for PATCH (partial update)."""

    schema_definition: dict[str, Any] | None = None
    is_active: bool | None = None


class EventSchemaResponse(BaseModel):
    """Event schema response."""

    id: str
    tenant_id: str
    event_type: str
    version: int
    is_active: bool
    schema_definition: dict[str, Any]
    created_by: str | None

    @field_validator("event_type", mode="before")
    @classmethod
    def _event_type_to_str(cls, v: EventType | str) -> str:
        """Accept EventType from DTO; serialize to str for JSON."""
        return v.value if isinstance(v, EventType) else v
