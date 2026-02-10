"""Permissions API: list permissions (tenant-scoped).

Uses only injected get_permission_repo; no manual repo construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_permission_repo
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail=f"Missing required header: {name}")
    return x_tenant_id


@router.get("")
async def list_permissions(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    skip: int = 0,
    limit: int = 200,
    permission_repo: PermissionRepository = Depends(get_permission_repo),
):
    """List permissions for tenant (paginated)."""
    perms = await permission_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return [
        {
            "id": p.id,
            "tenant_id": p.tenant_id,
            "code": p.code,
            "resource": p.resource,
            "action": p.action,
            "description": p.description,
        }
        for p in perms
    ]
