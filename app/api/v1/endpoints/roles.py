"""Roles API: list, get, create, update, delete, and role-permissions (tenant-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import (
    get_permission_repo_for_write,
    get_role_repo,
    get_role_repo_for_write,
    get_tenant_id,
)
from app.domain.exceptions import DuplicateAssignmentError
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.schemas.role import (
    RoleCreate,
    RolePermissionAssign,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter()


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo_for_write),
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Create a role (tenant-scoped). Optionally assign permissions by code."""
    existing = await role_repo.get_by_code_and_tenant(body.code, tenant_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{body.code}' already exists",
        )
    try:
        role = Role(
            tenant_id=tenant_id,
            code=body.code,
            name=body.name,
            description=body.description,
            is_system=False,
            is_active=True,
        )
        created = await role_repo.create(role)
        if body.permission_codes:
            for code in body.permission_codes:
                perm = await permission_repo.get_by_code_and_tenant(code, tenant_id)
                if perm:
                    try:
                        await permission_repo.assign_permission_to_role(
                            role_id=created.id,
                            permission_id=perm.id,
                            tenant_id=tenant_id,
                        )
                    except DuplicateAssignmentError:
                        pass
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid permission code: {code}",
                    )
        return RoleResponse.model_validate(created)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Role creation failed (constraint violation)",
        ) from None


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


@router.get("/{role_id}", response_model=RoleResponse)
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


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    body: RoleUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo_for_write),
):
    """Update role (name, description, is_active). Tenant-scoped."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="System roles cannot be updated")
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.is_active is not None:
        role.is_active = body.is_active
    updated = await role_repo.update(role)
    return RoleResponse.model_validate(updated)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo_for_write),
):
    """Deactivate role (soft delete). Tenant-scoped."""
    result = await role_repo.deactivate(role_id)
    if not result or result.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Role not found")


@router.post("/{role_id}/permissions", status_code=201)
async def assign_permission_to_role(
    role_id: str,
    body: RolePermissionAssign,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo),
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Assign a permission to a role. Tenant-scoped."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    try:
        await permission_repo.assign_permission_to_role(
            role_id=role_id,
            permission_id=body.permission_id,
            tenant_id=tenant_id,
        )
    except DuplicateAssignmentError:
        raise HTTPException(
            status_code=400,
            detail="Permission already assigned to role",
        ) from None
    return {"role_id": role_id, "permission_id": body.permission_id}


@router.delete("/{role_id}/permissions/{permission_id}", status_code=204)
async def remove_permission_from_role(
    role_id: str,
    permission_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo),
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Remove a permission from a role. Tenant-scoped."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    removed = await permission_repo.remove_permission_from_role(
        role_id=role_id,
        permission_id=permission_id,
        tenant_id=tenant_id,
    )
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Permission not assigned to role",
        )
