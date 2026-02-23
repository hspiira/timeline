"""OAuth provider config API: list, get, create, update, delete (tenant-scoped).

Uses only injected get_oauth_provider_config_repo / get_oauth_provider_config_repo_for_write.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    OAuthDriverRegistry,
    get_oauth_config_service,
    get_oauth_driver_registry,
    get_oauth_provider_config_repo,
    get_oauth_provider_config_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.dtos.user import UserResult
from app.infrastructure.services.oauth_config_service import OAuthConfigService
from app.core.limiter import limit_writes
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)
from app.schemas.oauth_provider_config import (
    OAuthAuthorizeResponse,
    OAuthCallbackTokenResponse,
    OAuthConfigAuditResponse,
    OAuthConfigCreateRequest,
    OAuthConfigResponse,
    OAuthConfigRotateRequest,
    OAuthConfigUpdate,
    OAuthHealthResponse,
    OAuthProviderMetadataItem,
    OAuthProvidersMetadataResponse,
)

router = APIRouter()


@router.get("", response_model=list[OAuthConfigResponse])
async def list_oauth_configs(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    include_inactive: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """List OAuth provider configs for tenant."""
    configs = await oauth_repo.list_configs(
        tenant_id=tenant_id,
        include_inactive=include_inactive,
        skip=skip,
        limit=limit,
    )
    return [OAuthConfigResponse.model_validate(c) for c in configs]


@router.post(
    "/{provider}/authorize",
    response_model=OAuthAuthorizeResponse,
)
@limit_writes
async def oauth_authorize(
    request: Request,
    provider: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(require_permission("oauth_config", "read"))],
    oauth_service: OAuthConfigService = Depends(get_oauth_config_service),
    return_url: str | None = None,
):
    """Build OAuth authorization URL and return it; frontend redirects user there."""
    url = await oauth_service.build_authorize_url(
        tenant_id=tenant_id,
        provider_type=provider,
        user_id=current_user.id,
        return_url=return_url,
    )
    return OAuthAuthorizeResponse(authorization_url=url)


@router.get(
    "/{provider}/callback",
    response_model=OAuthCallbackTokenResponse,
)
@limit_writes
async def oauth_callback(
    request: Request,
    provider: str,
    code: str,
    state: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_service: Annotated[OAuthConfigService, Depends(get_oauth_config_service)],
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Exchange code for tokens; verify state and return tokens. Tenant and provider must match state."""
    tokens = await oauth_service.exchange_callback(
        code=code,
        state=state,
        tenant_id=tenant_id,
        provider_type=provider,
    )
    return OAuthCallbackTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        scope=tokens.scope,
    )


@router.get(
    "/metadata/providers",
    response_model=OAuthProvidersMetadataResponse,
)
async def list_oauth_providers_metadata(
    oauth_driver_registry: OAuthDriverRegistry = Depends(get_oauth_driver_registry),
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Return list of supported OAuth providers (gmail, outlook, yahoo) and their endpoints."""
    providers = []
    for pt in oauth_driver_registry.list_providers():
        meta = oauth_driver_registry.get_provider_metadata(pt)
        providers.append(
            OAuthProviderMetadataItem(
                provider_type=meta["provider_type"],
                provider_name=meta["provider_name"],
                authorization_endpoint=meta["authorization_endpoint"],
                token_endpoint=meta["token_endpoint"],
                supports_pkce=meta.get("supports_pkce", False),
            )
        )
    return OAuthProvidersMetadataResponse(providers=providers)


@router.get("/active", response_model=OAuthConfigResponse)
async def get_active_oauth_config(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    provider_type: str,
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Get active OAuth provider config for tenant and provider type."""
    config = await oauth_repo.get_active_config(
        tenant_id=tenant_id,
        provider_type=provider_type,
    )
    if not config:
        raise HTTPException(status_code=404, detail="Active OAuth config not found")
    return OAuthConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=OAuthConfigResponse)
async def get_oauth_config(
    config_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Get OAuth provider config by id (tenant-scoped)."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return OAuthConfigResponse.model_validate(config)


@router.post("", response_model=OAuthConfigResponse, status_code=201)
@limit_writes
async def create_oauth_config(
    request: Request,
    body: OAuthConfigCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(require_permission("oauth_config", "create"))],
    oauth_service: OAuthConfigService = Depends(get_oauth_config_service),
):
    """Create OAuth provider config (envelope-encrypted credentials)."""
    config = await oauth_service.create_config(
        tenant_id=tenant_id,
        provider_type=body.provider_type,
        client_id=body.client_id,
        client_secret=body.client_secret,
        redirect_uri=body.redirect_uri,
        scopes=body.scopes or [],
        created_by=current_user.id,
    )
    return OAuthConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=OAuthConfigResponse)
@limit_writes
async def update_oauth_config(
    request: Request,
    config_id: str,
    body: OAuthConfigUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_service: OAuthConfigService = Depends(get_oauth_config_service),
    _: Annotated[object, Depends(require_permission("oauth_config", "update"))] = None,
):
    """Partially update OAuth provider config (display_name, redirect_uri, scopes)."""
    config = await oauth_service.update_config(
        config_id=config_id,
        tenant_id=tenant_id,
        display_name=body.display_name,
        redirect_uri=body.redirect_uri,
        redirect_uri_whitelist=body.redirect_uri_whitelist,
        allowed_scopes=body.allowed_scopes,
        default_scopes=body.default_scopes,
        tenant_configured_scopes=body.tenant_configured_scopes,
    )
    return OAuthConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=204)
@limit_writes
async def delete_oauth_config(
    request: Request,
    config_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(require_permission("oauth_config", "delete"))],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
):
    """Soft-delete OAuth provider config."""
    deleted = await oauth_repo.soft_delete(
        config_id=config_id,
        tenant_id=tenant_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return None


@router.post("/{config_id}/rotate", response_model=OAuthConfigResponse)
@limit_writes
async def rotate_oauth_config(
    request: Request,
    config_id: str,
    body: OAuthConfigRotateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(require_permission("oauth_config", "update"))],
    oauth_service: OAuthConfigService = Depends(get_oauth_config_service),
):
    """Rotate OAuth credentials: create new version with new client_id/client_secret."""
    new_config = await oauth_service.rotate_config(
        config_id=config_id,
        tenant_id=tenant_id,
        client_id=body.client_id,
        client_secret=body.client_secret,
        redirect_uri=body.redirect_uri,
        scopes=body.scopes,
        updated_by=current_user.id,
    )
    return OAuthConfigResponse.model_validate(new_config)


@router.get("/{config_id}/health", response_model=OAuthHealthResponse)
async def get_oauth_config_health(
    config_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Return health status for the OAuth provider config."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return OAuthHealthResponse(
        health_status=config.health_status or "unknown",
        last_health_check_at=config.last_health_check_at,
        last_health_error=config.last_health_error,
    )


# TODO: Implement OAuth config audit trail. Query audit entries via OAuthProviderConfigRepository
# (or dedicated audit repo) for config_id/tenant_id and return in OAuthConfigAuditResponse.entries.
# Track with: "OAuth config audit API" / audit trail implementation.


@router.get(
    "/{config_id}/audit",
    response_model=OAuthConfigAuditResponse,
)
async def get_oauth_config_audit(
    config_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Return audit log entries for this OAuth config. Stub: returns empty list until audit retrieval is implemented (see TODO above)."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return OAuthConfigAuditResponse(config_id=config_id, entries=[])
