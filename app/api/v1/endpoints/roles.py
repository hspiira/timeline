"""Roles API: list and get roles (tenant-scoped).

Uses only injected get_role_repo; no manual repo construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_role_repo, get_tenant_id
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.schemas.role import RoleResponse

router = APIRouter()


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    role_repo: RoleRepository = Depends(get_role_repo),
):
    """List roles for tenant (paginated)."""
    roles = await role_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
    )
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/{role_id}")
async def get_role(
    role_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo),
):
    """Get role by id (tenant-scoped)."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse.model_validate(role)
