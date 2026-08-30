"""OAuth provider config API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OAuthConfigCreateRequest(BaseModel):
    """Request body for creating or rotating OAuth provider config."""

    provider_type: str = Field(..., min_length=1, description="e.g. gmail, outlook, yahoo")
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    redirect_uri: str = Field(..., min_length=1)
    scopes: list[str] = Field(default_factory=list, description="OAuth scopes to request")


class OAuthConfigUpdate(BaseModel):
    """Request body for PATCH (partial update)."""

    display_name: str | None = Field(None, min_length=1)
    redirect_uri: str | None = Field(None, min_length=1)
    redirect_uri_whitelist: list[str] | None = None
    allowed_scopes: list[str] | None = None
    default_scopes: list[str] | None = None
    tenant_configured_scopes: list[str] | None = None


class OAuthAuthorizeResponse(BaseModel):
    """Response for authorize endpoint: URL to redirect user to."""

    authorization_url: str


class OAuthCallbackTokenResponse(BaseModel):
    """Response for callback: tokens (or redirect)."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
    scope: str


class OAuthConfigRotateRequest(BaseModel):
    """Request body for POST /{config_id}/rotate (new credentials)."""

    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    redirect_uri: str | None = None
    scopes: list[str] = Field(default_factory=list)


class OAuthHealthResponse(BaseModel):
    """Response for GET /{config_id}/health."""

    health_status: str
    last_health_check_at: datetime | None = None
    last_health_error: str | None = None


class OAuthProviderMetadataItem(BaseModel):
    """One supported provider for GET /metadata/providers."""

    provider_type: str
    provider_name: str
    authorization_endpoint: str
    token_endpoint: str
    supports_pkce: bool = False


class OAuthProvidersMetadataResponse(BaseModel):
    """Response for GET /metadata/providers."""

    providers: list[OAuthProviderMetadataItem]


class OAuthConfigAuditResponse(BaseModel):
    """Response for GET /{config_id}/audit (stub: entries list)."""

    config_id: str
    entries: list[dict] = []


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
