"""OAuth provider config API: list and get active config (tenant-scoped).

Uses only injected get_oauth_provider_config_repo; no manual construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_oauth_provider_config_repo
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail=f"Missing required header: {name}")
    return x_tenant_id


@router.get("/active")
async def get_active_oauth_config(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    provider_type: str,
    oauth_repo: OAuthProviderConfigRepository = Depends(get_oauth_provider_config_repo),
):
    """Get active OAuth provider config for tenant and provider type."""
    config = await oauth_repo.get_active_config(
        tenant_id=tenant_id,
        provider_type=provider_type,
    )
    if not config:
        raise HTTPException(status_code=404, detail="Active OAuth config not found")
    return {
        "id": config.id,
        "tenant_id": config.tenant_id,
        "provider_type": config.provider_type,
        "display_name": config.display_name,
        "version": config.version,
        "is_active": config.is_active,
        "health_status": getattr(config, "health_status", None),
    }


@router.get("/{config_id}")
async def get_oauth_config(
    config_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    oauth_repo: OAuthProviderConfigRepository = Depends(get_oauth_provider_config_repo),
):
    """Get OAuth provider config by id (tenant-scoped)."""
    config = await oauth_repo.get_by_id(config_id)
    if not config or config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="OAuth config not found")
    return {
        "id": config.id,
        "tenant_id": config.tenant_id,
        "provider_type": config.provider_type,
        "display_name": config.display_name,
        "version": config.version,
        "is_active": config.is_active,
        "health_status": getattr(config, "health_status", None),
    }
