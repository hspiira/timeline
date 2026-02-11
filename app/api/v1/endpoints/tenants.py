"""Tenant API: thin routes delegating to TenantCreationService and tenant repo (Postgres or Firestore)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_tenant_creation_service,
    get_tenant_repo,
    get_tenant_repo_for_write,
)
from app.application.interfaces.repositories import ITenantRepository
from app.application.services.tenant_creation_service import TenantCreationService
from app.domain.enums import TenantStatus
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantResponse,
    TenantStatusUpdate,
    TenantUpdate,
)

router = APIRouter()


@router.post("", response_model=TenantCreateResponse, status_code=201)
async def create_tenant(
    body: TenantCreateRequest,
    tenant_svc: TenantCreationService = Depends(get_tenant_creation_service),
):
    """Create a new tenant with admin user and RBAC. Only name and tenant code required; admin password is auto-generated."""
    try:
        result = await tenant_svc.create_tenant(
            code=body.code,
            name=body.name,
        )
        return TenantCreateResponse(
            tenant_id=result.tenant_id,
            tenant_code=result.tenant_code,
            tenant_name=result.tenant_name,
            admin_username=result.admin_username,
            admin_password=result.admin_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo)],
    skip: int = 0,
    limit: int = 100,
):
    """List active tenants (paginated)."""
    tenants = await tenant_repo.get_active_tenants(skip=skip, limit=limit)
    return [
        TenantResponse(id=t.id, code=t.code, name=t.name, status=t.status)
        for t in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo)],
):
    """Get tenant by id."""
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=tenant.id, code=tenant.code, name=tenant.name, status=tenant.status
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
):
    """Update tenant name and/or status."""
    updated = await tenant_repo.update_tenant(
        tenant_id, name=body.name, status=body.status
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=updated.id,
        code=updated.code,
        name=updated.name,
        status=updated.status,
    )


@router.patch("/{tenant_id}/status", response_model=TenantResponse)
async def update_tenant_status(
    tenant_id: str,
    body: TenantStatusUpdate,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
):
    """Update tenant status (active, suspended, archived)."""
    updated = await tenant_repo.update_status(tenant_id, body.new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=updated.id,
        code=updated.code,
        name=updated.name,
        status=updated.status,
    )


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: str,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
):
    """Soft-delete tenant by setting status to archived."""
    updated = await tenant_repo.update_status(tenant_id, TenantStatus.ARCHIVED)
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return None
