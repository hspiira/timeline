"""Permission API schemas."""

from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    """Request body for creating a permission."""

    code: str = Field(..., min_length=1, max_length=128)
    resource: str = Field(..., min_length=1, max_length=64)
    action: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)


class PermissionResponse(BaseModel):
    """Permission list/detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    code: str
    resource: str
    action: str
    description: str | None
