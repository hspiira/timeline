"""Roles API: list, get, create, update, delete, and role-permissions (tenant-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import (
    get_permission_repo,
    get_permission_repo_for_write,
    get_role_permission_repo_for_write,
    get_role_repo,
    get_role_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.core.limiter import limit_writes
from app.domain.exceptions import DuplicateAssignmentError
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.infrastructure.persistence.repositories.role_permission_repo import (
    RolePermissionRepository,
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
@limit_writes
async def create_role(
    request: Request,
    body: RoleCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo_for_write),
    permission_repo: PermissionRepository = Depends(get_permission_repo),
    role_permission_repo: RolePermissionRepository = Depends(
        get_role_permission_repo_for_write
    ),
    _: Annotated[object, Depends(require_permission("role", "create"))] = None,
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
                        await role_permission_repo.assign_permission_to_role(
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
    _: Annotated[object, Depends(require_permission("role", "read"))] = None,
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
    _: Annotated[object, Depends(require_permission("role", "read"))] = None,
):
    """Get role by id (tenant-scoped)."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
@limit_writes
async def update_role(
    request: Request,
    role_id: str,
    body: RoleUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo_for_write),
    _: Annotated[object, Depends(require_permission("role", "update"))] = None,
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
@limit_writes
async def delete_role(
    request: Request,
    role_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo_for_write),
    _: Annotated[object, Depends(require_permission("role", "delete"))] = None,
):
    """Deactivate role (soft delete). Tenant-scoped."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    result = await role_repo.deactivate(role_id)
    if not result:
        raise HTTPException(status_code=404, detail="Role not found")


@router.post("/{role_id}/permissions", status_code=201)
@limit_writes
async def assign_permission_to_role(
    request: Request,
    role_id: str,
    body: RolePermissionAssign,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo),
    role_permission_repo: RolePermissionRepository = Depends(
        get_role_permission_repo_for_write
    ),
    _: Annotated[object, Depends(require_permission("role", "update"))] = None,
):
    """Assign a permission to a role. Tenant-scoped."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    try:
        await role_permission_repo.assign_permission_to_role(
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
@limit_writes
async def remove_permission_from_role(
    request: Request,
    role_id: str,
    permission_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    role_repo: RoleRepository = Depends(get_role_repo),
    role_permission_repo: RolePermissionRepository = Depends(
        get_role_permission_repo_for_write
    ),
    _: Annotated[object, Depends(require_permission("role", "update"))] = None,
):
    """Remove a permission from a role. Tenant-scoped."""
    role = await role_repo.get_by_id_and_tenant(role_id, tenant_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    removed = await role_permission_repo.remove_permission_from_role(
        role_id=role_id,
        permission_id=permission_id,
        tenant_id=tenant_id,
    )
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Permission not assigned to role",
        )
