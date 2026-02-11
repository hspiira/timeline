"""User-roles API: list roles for user (including /me/roles), assign/remove role."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    get_role_repo,
    get_tenant_id,
    get_user_repo,
    get_user_role_repo,
    get_user_role_repo_for_write,
    require_permission,
)
from app.application.dtos.user import UserResult
from app.core.limiter import limit_writes
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.persistence.repositories.user_role_repo import (
    UserRoleRepository,
)
from app.schemas.role import RoleResponse

router = APIRouter()


@router.get("/me/roles", response_model=list[RoleResponse])
async def list_my_roles(
    current_user: Annotated[UserResult, Depends(require_permission("user_role", "read"))],
    user_role_repo: UserRoleRepository = Depends(get_user_role_repo),
):
    """List roles assigned to the current authenticated user."""
    roles = await user_role_repo.get_user_roles(
        user_id=current_user.id, tenant_id=current_user.tenant_id
    )
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/{user_id}/roles", response_model=list[RoleResponse])
async def list_user_roles(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    user_role_repo: UserRoleRepository = Depends(get_user_role_repo),
    _: Annotated[object, Depends(require_permission("user_role", "read"))] = None,
):
    """List roles assigned to a user (tenant-scoped)."""
    roles = await user_role_repo.get_user_roles(user_id=user_id, tenant_id=tenant_id)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/{user_id}/roles/{role_id}", status_code=204)
@limit_writes
async def assign_role_to_user(
    request: Request,
    user_id: str,
    role_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    user_repo: UserRepository = Depends(get_user_repo),
    role_repo: RoleRepository = Depends(get_role_repo),
    user_role_repo: UserRoleRepository = Depends(get_user_role_repo_for_write),
    _: Annotated[object, Depends(require_permission("user_role", "update"))] = None,
):
    """Assign a role to a user (tenant-scoped). Verifies user and role exist and belong to tenant."""
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    await user_role_repo.assign_role_to_user(
        user_id=user_id,
        role_id=role_id,
        tenant_id=tenant_id,
    )
    return None


@router.delete("/{user_id}/roles/{role_id}", status_code=204)
@limit_writes
async def remove_role_from_user(
    request: Request,
    user_id: str,
    role_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    user_role_repo: UserRoleRepository = Depends(get_user_role_repo_for_write),
    _: Annotated[object, Depends(require_permission("user_role", "update"))] = None,
):
    """Remove a role from a user (tenant-scoped)."""
    removed = await user_role_repo.remove_role_from_user(
        user_id=user_id, role_id=role_id, tenant_id=tenant_id
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return None
