"""Role API schemas."""

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    """Request body for creating a role."""

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] = Field(default_factory=list, max_length=100)


class RoleUpdate(BaseModel):
    """Request body for updating a role (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class RolePermissionAssign(BaseModel):
    """Request body for assigning a permission to a role."""

    permission_id: str


class RoleResponse(BaseModel):
    """Role list/detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None
    is_system: bool
    is_active: bool

