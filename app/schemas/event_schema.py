"""Event schema (payload validation) API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class EventSchemaCreateRequest(BaseModel):
    """Request body for creating an event schema version."""

    event_type: str = Field(..., min_length=1, max_length=128)
    schema_definition: dict[str, Any] = Field(...)
    is_active: bool = False
    created_by: str | None = None


class EventSchemaResponse(BaseModel):
    """Event schema response."""

    id: str
    tenant_id: str
    event_type: str
    version: int
    is_active: bool
    schema_definition: dict[str, Any]
    created_by: str | None
