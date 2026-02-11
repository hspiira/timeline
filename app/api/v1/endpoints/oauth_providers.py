"""OAuth provider config API: list, get, create, update, delete (tenant-scoped).

Uses only injected get_oauth_provider_config_repo / get_oauth_provider_config_repo_for_write.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    EnvelopeEncryptor,
    OAuthDriverRegistry,
    get_envelope_encryptor,
    get_oauth_driver_registry,
    get_oauth_provider_config_repo,
    get_oauth_provider_config_repo_for_write,
    get_oauth_state_repo,
    get_tenant_id,
    require_permission,
)
from app.core.limiter import limit_writes
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)
from app.infrastructure.persistence.repositories.oauth_state_repo import (
    OAuthStateRepository,
)
from app.schemas.oauth_provider_config import (
    OAuthAuthorizeResponse,
    OAuthCallbackTokenResponse,
    OAuthConfigCreate,
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
    skip: int = 0,
    limit: int = 100,
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
    current_user: Annotated[object, Depends(require_permission("oauth_config", "read"))],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    state_repo: Annotated[
        OAuthStateRepository, Depends(get_oauth_state_repo)
    ],
    return_url: str | None = None,
    envelope_encryptor: EnvelopeEncryptor = Depends(get_envelope_encryptor),
    oauth_driver_registry: OAuthDriverRegistry = Depends(get_oauth_driver_registry),
):
    """Build OAuth authorization URL and return it; frontend redirects user there."""
    provider_type = provider.strip().lower()
    config = await oauth_repo.get_active_config(tenant_id=tenant_id, provider_type=provider_type)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No active OAuth config for provider: {provider_type}",
        )
    user_id = getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User id required")
    _, signed_state = await state_repo.create_state(
        tenant_id=tenant_id,
        user_id=user_id,
        provider_config_id=config.id,
        return_url=return_url,
    )
    try:
        creds = envelope_encryptor.decrypt(config.client_id_encrypted)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt OAuth credentials",
        )
    if isinstance(creds, dict):
        client_id = creds.get("client_id", "")
        client_secret = creds.get("client_secret", "")
    else:
        raise HTTPException(status_code=500, detail="Invalid credential format")
    scopes = config.default_scopes or config.allowed_scopes or []
    driver = oauth_driver_registry.get_driver(
        provider_type=provider_type,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=config.redirect_uri,
        scopes=scopes,
    )
    authorization_url = driver.build_authorization_url(state=signed_state)
    return OAuthAuthorizeResponse(authorization_url=authorization_url)


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
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    state_repo: Annotated[
        OAuthStateRepository, Depends(get_oauth_state_repo)
    ],
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
    envelope_encryptor: EnvelopeEncryptor = Depends(get_envelope_encryptor),
    oauth_driver_registry: OAuthDriverRegistry = Depends(get_oauth_driver_registry),
):
    """Exchange code for tokens; verify state and return tokens."""
    from app.infrastructure.external.email.envelope_encryption import (
        OAuthStateManager,
    )

    try:
        state_manager = OAuthStateManager()
        state_id = state_manager.verify_and_extract(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    state_row = await state_repo.consume(state_id)
    if not state_row:
        raise HTTPException(
            status_code=400,
            detail="State already used or expired",
        )
    config = await oauth_repo.get_by_id_and_tenant(
        state_row.provider_config_id, state_row.tenant_id or ""
    )
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    try:
        creds = envelope_encryptor.decrypt(config.client_id_encrypted)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt OAuth credentials",
        )
    if not isinstance(creds, dict):
        raise HTTPException(status_code=500, detail="Invalid credential format")
    client_id = creds.get("client_id", "")
    client_secret = creds.get("client_secret", "")
    scopes = config.default_scopes or config.allowed_scopes or []
    driver = oauth_driver_registry.get_driver(
        provider_type=config.provider_type,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=config.redirect_uri,
        scopes=scopes,
    )
    try:
        tokens = await driver.exchange_code_for_tokens(code=code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    body: OAuthConfigCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(require_permission("oauth_config", "create"))],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    envelope_encryptor: EnvelopeEncryptor = Depends(get_envelope_encryptor),
):
    """Create or rotate OAuth provider config (envelope-encrypted credentials)."""
    envelope = envelope_encryptor.encrypt(
        {"client_id": body.client_id, "client_secret": body.client_secret}
    )
    key_id = envelope_encryptor.extract_key_id(envelope)
    config = await oauth_repo.create_new_version(
        tenant_id=tenant_id,
        provider_type=body.provider_type.strip().lower(),
        client_id_encrypted=envelope,
        client_secret_encrypted=envelope,
        encryption_key_id=key_id,
        redirect_uri=body.redirect_uri.strip(),
        scopes=body.scopes or [],
        created_by=getattr(current_user, "id", None),
    )
    return OAuthConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=OAuthConfigResponse)
@limit_writes
async def update_oauth_config(
    request: Request,
    config_id: str,
    body: OAuthConfigUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("oauth_config", "update"))] = None,
):
    """Partially update OAuth provider config (display_name, redirect_uri, scopes)."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    if body.display_name is not None:
        config.display_name = body.display_name
    if body.redirect_uri is not None:
        config.redirect_uri = body.redirect_uri
    if body.redirect_uri_whitelist is not None:
        config.redirect_uri_whitelist = body.redirect_uri_whitelist
    if body.allowed_scopes is not None:
        config.allowed_scopes = body.allowed_scopes
    if body.default_scopes is not None:
        config.default_scopes = body.default_scopes
    if body.tenant_configured_scopes is not None:
        config.tenant_configured_scopes = body.tenant_configured_scopes
    await oauth_repo.update(config)
    return OAuthConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=204)
@limit_writes
async def delete_oauth_config(
    request: Request,
    config_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(require_permission("oauth_config", "delete"))],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
):
    """Soft-delete OAuth provider config."""
    deleted = await oauth_repo.soft_delete(
        config_id=config_id,
        tenant_id=tenant_id,
        deleted_by=getattr(current_user, "id", None),
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
    current_user: Annotated[object, Depends(require_permission("oauth_config", "update"))],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    envelope_encryptor: EnvelopeEncryptor = Depends(get_envelope_encryptor),
):
    """Rotate OAuth credentials: create new version with new client_id/client_secret."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    redirect_uri = body.redirect_uri or config.redirect_uri
    scopes = body.scopes or config.default_scopes or config.allowed_scopes or []
    envelope = envelope_encryptor.encrypt(
        {"client_id": body.client_id, "client_secret": body.client_secret}
    )
    key_id = envelope_encryptor.extract_key_id(envelope)
    new_config = await oauth_repo.create_new_version(
        tenant_id=tenant_id,
        provider_type=config.provider_type,
        client_id_encrypted=envelope,
        client_secret_encrypted=envelope,
        encryption_key_id=key_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        display_name=config.display_name,
        created_by=getattr(current_user, "id", None),
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


@router.get("/{config_id}/audit")
async def get_oauth_config_audit(
    config_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    _: Annotated[object, Depends(require_permission("oauth_config", "read"))] = None,
):
    """Return audit log entries for this OAuth config (stub: empty list until audit repo)."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return {"config_id": config_id, "entries": []}
