"""Permission API schemas."""

from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    """Permission list/detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    code: str
    resource: str
    action: str
    description: str | None
