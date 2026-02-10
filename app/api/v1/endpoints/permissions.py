"""Permissions API: list, get, create, delete (tenant-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import (
    get_permission_repo,
    get_permission_repo_for_write,
    get_tenant_id,
)
from app.infrastructure.persistence.models.permission import Permission
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.schemas.permission import PermissionCreate, PermissionResponse

router = APIRouter()


@router.post("", response_model=PermissionResponse, status_code=201)
async def create_permission(
    body: PermissionCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Create a permission (tenant-scoped)."""
    existing = await permission_repo.get_by_code_and_tenant(body.code, tenant_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Permission with code '{body.code}' already exists",
        )
    try:
        perm = Permission(
            tenant_id=tenant_id,
            code=body.code,
            resource=body.resource,
            action=body.action,
            description=body.description,
        )
        created = await permission_repo.create(perm)
        return PermissionResponse.model_validate(created)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Permission creation failed (constraint violation)",
        ) from None


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
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


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    permission_repo: PermissionRepository = Depends(get_permission_repo),
):
    """Get permission by id (tenant-scoped)."""
    perm = await permission_repo.get_by_id(permission_id)
    if not perm or perm.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Permission not found")
    return PermissionResponse.model_validate(perm)


@router.delete("/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    permission_repo: PermissionRepository = Depends(get_permission_repo_for_write),
):
    """Delete permission. Tenant-scoped."""
    perm = await permission_repo.get_by_id(permission_id)
    if not perm or perm.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Permission not found")
    await permission_repo.delete(perm)
