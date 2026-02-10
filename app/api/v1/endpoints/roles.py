"""Roles API: list and get roles (tenant-scoped).

Uses only injected get_role_repo; no manual repo construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_role_repo
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.role_repo import RoleRepository

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail=f"Missing required header: {name}")
    return x_tenant_id


@router.get("")
async def list_roles(
    tenant_id: Annotated[str, Depends(_tenant_id)],
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
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "code": r.code,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "is_active": r.is_active,
        }
        for r in roles
    ]


@router.get("/{role_id}")
async def get_role(
    role_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo),
):
    """Get role by id (tenant-scoped)."""
    role = await role_repo.get_by_id(role_id)
    if not role or role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Role not found")
    return {
        "id": role.id,
        "tenant_id": role.tenant_id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
    }
