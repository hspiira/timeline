"""Permissions API: list permissions (tenant-scoped).

Uses only injected get_permission_repo; no manual repo construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_current_user, get_permission_repo, get_tenant_id
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.schemas.permission import PermissionResponse

router = APIRouter()


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
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
    return [PermissionResponse.model_validate(p) for p in perms]
