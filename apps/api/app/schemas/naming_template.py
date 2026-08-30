"""Naming template API schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NamingTemplateCreateRequest(BaseModel):
    """Request body for creating a naming template."""

    scope_type: str = Field(..., pattern="^(flow|subject|document)$")
    scope_id: str = Field(..., min_length=1)
    template_string: str = Field(..., min_length=1, max_length=500)
    placeholders: list[dict[str, Any]] | None = None


class NamingTemplateUpdateRequest(BaseModel):
    """Request body for updating a naming template (partial)."""

    template_string: str | None = Field(default=None, min_length=1, max_length=500)
    placeholders: list[dict[str, Any]] | None = None


class NamingTemplateResponse(BaseModel):
    """Naming template response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    scope_type: str
    scope_id: str
    template_string: str
    placeholders: list[dict[str, Any]] | None
