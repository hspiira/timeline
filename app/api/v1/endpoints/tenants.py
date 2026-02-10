"""Tenant API: thin routes delegating to TenantCreationService and TenantRepository."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_tenant_creation_service, get_tenant_repo
from app.application.services.tenant_creation_service import TenantCreationService
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.schemas.tenant import TenantCreateRequest, TenantCreateResponse

router = APIRouter()


@router.post("", response_model=TenantCreateResponse, status_code=201)
async def create_tenant(
    body: TenantCreateRequest,
    tenant_svc: TenantCreationService = Depends(get_tenant_creation_service),
):
    """Create a new tenant with admin user and RBAC (permissions, roles, audit schema)."""
    try:
        result = await tenant_svc.create_tenant(
            code=body.code,
            name=body.name,
            admin_password=body.admin_password,
        )
        return TenantCreateResponse(
            tenant_id=result.tenant_id,
            tenant_code=result.tenant_code,
            tenant_name=result.tenant_name,
            admin_username=result.admin_username,
            admin_password=result.admin_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
):
    """List active tenants (paginated)."""
    tenants = await tenant_repo.get_active_tenants(skip=skip, limit=limit)
    return [
        {"id": t.id, "code": t.code, "name": t.name, "status": t.status}
        for t in tenants
    ]


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
):
    """Get tenant by id."""
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "id": tenant.id,
        "code": tenant.code,
        "name": tenant.name,
        "status": tenant.status,
    }
