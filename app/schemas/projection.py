"""Pydantic schemas for projection API (Phase 5)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectionDefinitionCreateRequest(BaseModel):
    """Request body for creating a projection definition."""

    name: str = Field(..., min_length=1, description="Projection name (must match a registered handler)")
    version: int = Field(..., ge=1, description="Projection version (must match handler)")
    subject_type: str | None = Field(
        default=None,
        description="Subject type filter; null = all subject types",
    )


class ProjectionDefinitionResponse(BaseModel):
    """Projection definition in list/detail."""

    id: str
    tenant_id: str
    name: str
    version: int
    subject_type: str | None
    last_event_seq: int
    active: bool
    created_at: datetime


class ProjectionStateResponse(BaseModel):
    """Projection state for one subject."""

    subject_id: str
    state: dict[str, Any] = Field(default_factory=dict)


class ProjectionStateListItem(BaseModel):
    """Projection state in list (subject_id + state)."""

    id: str
    projection_id: str
    subject_id: str
    state: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime
