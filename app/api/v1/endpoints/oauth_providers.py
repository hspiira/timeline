"""OAuth provider config API: list and get active config (tenant-scoped).

Uses only injected get_oauth_provider_config_repo; no manual construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_oauth_provider_config_repo, get_tenant_id
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)
from app.schemas.oauth_provider_config import OAuthConfigResponse

router = APIRouter()


@router.get("/active", response_model=OAuthConfigResponse)
async def get_active_oauth_config(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo)
    ],
    provider_type: str,
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
):
    """Get OAuth provider config by id (tenant-scoped)."""
    config = await oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return OAuthConfigResponse.model_validate(config)
