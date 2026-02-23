"""Subject relationship API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubjectRelationshipCreateRequest(BaseModel):
    """Request body for creating a subject relationship."""

    target_subject_id: str = Field(..., min_length=1, description="Target subject ID")
    relationship_kind: str = Field(
        ..., min_length=1, max_length=100, description="e.g. client_of, parent_of"
    )
    payload: dict[str, Any] | None = Field(default=None)


class SubjectRelationshipResponse(BaseModel):
    """Subject relationship response."""

    id: str
    tenant_id: str
    source_subject_id: str
    target_subject_id: str
    relationship_kind: str
    payload: dict[str, Any] | None
    created_at: datetime


class SubjectRelationshipListItem(BaseModel):
    """Subject relationship list item (same as response for now)."""

    id: str
    tenant_id: str
    source_subject_id: str
    target_subject_id: str
    relationship_kind: str
    payload: dict[str, Any] | None
    created_at: datetime
