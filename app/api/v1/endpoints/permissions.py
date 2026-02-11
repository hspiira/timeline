"""Permissions API: list, get, create, delete (tenant-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import (
    get_permission_repo,
    get_permission_repo_for_write,
    get_permission_service,
    get_tenant_id,
    require_permission,
)
from app.application.services.permission_service import PermissionService
from app.core.limiter import limit_writes
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.schemas.permission import PermissionCreateRequest, PermissionResponse

router = APIRouter()


@router.post("", response_model=PermissionResponse, status_code=201)
@limit_writes
async def create_permission(
    request: Request,
    body: PermissionCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    permission_service: Annotated[
        PermissionService, Depends(get_permission_service)
    ],
    _: Annotated[object, Depends(require_permission("permission", "create"))] = None,
):
    """Create a permission (tenant-scoped)."""
    try:
        created = await permission_service.create_permission(
            tenant_id=tenant_id,
            code=body.code,
            resource=body.resource,
            action=body.action,
            description=body.description,
        )
        return PermissionResponse.model_validate(created)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Permission creation failed (constraint violation)",
        ) from None


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    permission_repo: Annotated[
        PermissionRepository, Depends(get_permission_repo)
    ],
    _: Annotated[object, Depends(require_permission("permission", "read"))] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
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
    permission_repo: Annotated[
        PermissionRepository, Depends(get_permission_repo)
    ],
    _: Annotated[object, Depends(require_permission("permission", "read"))] = None,
):
    """Get permission by id (tenant-scoped)."""
    perm = await permission_repo.get_by_id_and_tenant(permission_id, tenant_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    return PermissionResponse.model_validate(perm)


@router.delete("/{permission_id}", status_code=204)
@limit_writes
async def delete_permission(
    request: Request,
    permission_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    permission_repo: Annotated[
        PermissionRepository, Depends(get_permission_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("permission", "delete"))] = None,
):
    """Delete permission. Tenant-scoped."""
    perm = await permission_repo.get_by_id_and_tenant(permission_id, tenant_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    await permission_repo.delete(perm)
