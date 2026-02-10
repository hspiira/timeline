"""User-roles API: list roles for user, assign/remove role.

Uses only injected get_permission_repo and get_role_repo; no manual construction.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import (
    get_permission_repo,
    get_permission_repo_for_write,
    get_role_repo,
    get_user_repo,
)
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.permission_repo import PermissionRepository
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail=f"Missing required header: {name}")
    return x_tenant_id


@router.get("/{user_id}/roles")
async def list_user_roles(
    user_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    permission_repo: PermissionRepository = Depends(get_permission_repo),
):
    """List roles assigned to a user (tenant-scoped)."""
    roles = await permission_repo.get_user_roles(user_id=user_id, tenant_id=tenant_id)
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


@router.post("/{user_id}/roles/{role_id}", status_code=204)
async def assign_role_to_user(
    user_id: str,
    role_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    user_repo: UserRepository = Depends(get_user_repo),
    role_repo: RoleRepository = Depends(get_role_repo),
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Assign a role to a user (tenant-scoped). Verifies user and role exist and belong to tenant."""
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = await role_repo.get_by_id(role_id)
    if not role or role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Role not found")
    await permission_repo.assign_role_to_user(
        user_id=user_id,
        role_id=role_id,
        tenant_id=tenant_id,
    )
    return None


@router.delete("/{user_id}/roles/{role_id}", status_code=204)
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Remove a role from a user (tenant-scoped)."""
    removed = await permission_repo.remove_role_from_user(user_id=user_id, role_id=role_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return None
