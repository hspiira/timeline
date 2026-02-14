"""Document category configuration API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class DocumentCategoryCreateRequest(BaseModel):
    """Request body for creating a document category."""

    category_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    metadata_schema: dict[str, Any] | None = Field(default=None)
    default_retention_days: int | None = Field(default=None, ge=1)
    is_active: bool = True


class DocumentCategoryUpdateRequest(BaseModel):
    """Request body for PATCH (partial update)."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    metadata_schema: dict[str, Any] | None = None
    default_retention_days: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class DocumentCategoryListItem(BaseModel):
    """Document category list item."""

    id: str
    tenant_id: str
    category_name: str
    display_name: str
    description: str | None
    default_retention_days: int | None
    is_active: bool


class DocumentCategoryResponse(BaseModel):
    """Document category full response."""

    id: str
    tenant_id: str
    category_name: str
    display_name: str
    description: str | None
    metadata_schema: dict[str, Any] | None
    default_retention_days: int | None
    is_active: bool
