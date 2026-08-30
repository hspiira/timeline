"""Relationship kind API schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RelationshipKindCreateRequest(BaseModel):
    """Request body for creating a relationship kind."""

    kind: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="e.g. client_of, parent_of",
    )
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    payload_schema: dict[str, Any] | None = Field(default=None)


class RelationshipKindUpdateRequest(BaseModel):
    """Request body for PATCH (partial update)."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    payload_schema: dict[str, Any] | None = None


class RelationshipKindResponse(BaseModel):
    """Relationship kind response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    kind: str
    display_name: str
    description: str | None
    payload_schema: dict[str, Any] | None


class RelationshipKindListItem(BaseModel):
    """Relationship kind list item."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    kind: str
    display_name: str
    description: str | None
    payload_schema: dict[str, Any] | None
