"""Role API schemas."""

from pydantic import BaseModel, ConfigDict


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

