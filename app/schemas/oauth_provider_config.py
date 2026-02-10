"""OAuth provider config API schemas."""

from pydantic import BaseModel, ConfigDict


class OAuthConfigResponse(BaseModel):
    """Response model for OAuth provider config (list/detail)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    provider_type: str
    display_name: str
    version: int
    is_active: bool
    health_status: str | None = None
