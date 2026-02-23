"""User-roles API: list roles for user (including /me/roles), assign/remove role."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_authorization_service,
    get_current_user,
    get_role_repo,
    get_tenant_id,
    get_user_repo,
    get_user_role_repo,
    get_user_role_repo_for_write,
    require_permission,
)
from app.application.dtos.user import UserResult
from app.application.services.authorization_service import AuthorizationService
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
    user_role_repo: Annotated[UserRoleRepository, Depends(get_user_role_repo)],
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
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    user_role_repo: Annotated[UserRoleRepository, Depends(get_user_role_repo)],
    _: Annotated[object, Depends(require_permission("user_role", "read"))] = None,
):
    """List roles assigned to a user (tenant-scoped). Returns 404 if user does not exist."""
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = await user_role_repo.get_user_roles(user_id=user_id, tenant_id=tenant_id)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/{user_id}/roles/{role_id}", status_code=204)
@limit_writes
async def assign_role_to_user(
    request: Request,
    user_id: str,
    role_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(get_current_user)],
    auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    role_repo: Annotated[RoleRepository, Depends(get_role_repo)],
    user_role_repo: Annotated[UserRoleRepository, Depends(get_user_role_repo_for_write)],
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Assign a role to a user (tenant-scoped). Admin role requires user_role:assign_admin; other roles require user_role:update."""
    user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.code == "admin":
        await auth_svc.require_permission(current_user.id, tenant_id, "user_role", "assign_admin")
    else:
        await auth_svc.require_permission(current_user.id, tenant_id, "user_role", "update")
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
    current_user: Annotated[UserResult, Depends(get_current_user)],
    auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
    role_repo: Annotated[RoleRepository, Depends(get_role_repo)],
    user_role_repo: Annotated[UserRoleRepository, Depends(get_user_role_repo_for_write)],
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Remove a role from a user (tenant-scoped). Admin role requires user_role:assign_admin; other roles require user_role:update."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.code == "admin":
        await auth_svc.require_permission(current_user.id, tenant_id, "user_role", "assign_admin")
    else:
        await auth_svc.require_permission(current_user.id, tenant_id, "user_role", "update")
    removed = await user_role_repo.remove_role_from_user(
        user_id=user_id, role_id=role_id, tenant_id=tenant_id
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return None
