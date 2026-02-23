"""Tenant API: thin routes delegating to TenantCreationService and tenant repo (Postgres or Firestore)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    DbOrFirestore,
    get_tenant_creation_service,
    get_tenant_id,
    get_tenant_repo,
    get_tenant_repo_for_write,
    get_verified_tenant_id,
    require_permission,
    _get_db_or_firestore_write,
)
from app.application.dtos.user import UserResult
from app.application.interfaces.repositories import ITenantRepository
from app.application.services.tenant_creation_service import TenantCreationService
from app.core.config import get_settings
from app.core.limiter import limit_create_tenant, limit_writes
from app.domain.enums import TenantStatus
from app.infrastructure.services.api_audit_log_service import ApiAuditLogService
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantResponse,
    TenantStatusUpdate,
    TenantUpdate,
)

router = APIRouter()


@router.post("", response_model=TenantCreateResponse, status_code=201)
@limit_create_tenant
async def create_tenant(
    request: Request,
    body: TenantCreateRequest,
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_write)],
    tenant_svc: TenantCreationService = Depends(get_tenant_creation_service),
):
    """Create a new tenant with admin user and RBAC.

    This endpoint is protected by a shared secret header:
    - Settings must define CREATE_TENANT_SECRET.
    - Requests must include X-Create-Tenant-Secret matching that value.
    """
    settings = get_settings()
    if not settings.create_tenant_secret:
        raise HTTPException(
            status_code=503,
            detail="Tenant creation is not configured (CREATE_TENANT_SECRET is not set).",
        )

    header_secret = request.headers.get("X-Create-Tenant-Secret")
    expected = settings.create_tenant_secret.get_secret_value()
    if not header_secret or header_secret != expected:
        raise HTTPException(status_code=401, detail="Unauthorized tenant creation")

    try:
        admin_password = (
            body.admin_initial_password.get_secret_value()
            if body.admin_initial_password is not None
            else None
        )
        result = await tenant_svc.create_tenant(
            code=body.code,
            name=body.name,
            admin_initial_password=admin_password,
        )
        # API audit log: tenant creation has no JWT/tenant header; log in same transaction (Postgres only).
        settings = get_settings()
        if settings.database_backend == "postgres" and backend.db is not None:
            request_id = getattr(request.state, "request_id", None)
            client_host = request.client.host if request.client else None
            forwarded = request.headers.get("X-Forwarded-For")
            ip_address = (forwarded.split(",")[0].strip() if forwarded else None) or client_host
            user_agent = request.headers.get("User-Agent")
            svc = ApiAuditLogService(backend.db)
            await svc.log_action(
                tenant_id=result.tenant_id,
                user_id=None,
                action="create",
                resource_type="tenants",
                resource_id=result.tenant_id,
                old_values=None,
                new_values=None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                success=True,
                error_message=None,
            )
        set_password_url = None
        if result.set_password_token and settings.set_password_base_url:
            base = settings.set_password_base_url.rstrip("/")
            set_password_url = f"{base}/set-password?token={result.set_password_token}"
        return TenantCreateResponse(
            tenant_id=result.tenant_id,
            tenant_code=result.tenant_code,
            tenant_name=result.tenant_name,
            admin_username=result.admin_username,
            admin_email=result.admin_email,
            set_password_url=set_password_url,
            set_password_expires_at=result.set_password_expires_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo)],
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Return the current tenant only (tenant:read grants access to own tenant; no cross-tenant enumeration)."""
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return [
        TenantResponse(id=tenant.id, code=tenant.code, name=tenant.name, status=tenant.status)
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo)],
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Get tenant by id. Path tenant_id must match X-Tenant-ID header."""
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=tenant.id, code=tenant.code, name=tenant.name, status=tenant.status
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
@limit_writes
async def update_tenant(
    request: Request,
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    body: TenantUpdate,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
    _: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
):
    """Update tenant name and/or status. Path tenant_id must match X-Tenant-ID header."""
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
@limit_writes
async def update_tenant_status(
    request: Request,
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    body: TenantStatusUpdate,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
    _: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
):
    """Update tenant status. Path tenant_id must match X-Tenant-ID header."""
    updated = await tenant_repo.update_tenant(tenant_id, status=body.new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=updated.id,
        code=updated.code,
        name=updated.name,
        status=updated.status,
    )


@router.delete("/{tenant_id}", status_code=204)
@limit_writes
async def delete_tenant(
    request: Request,
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_write)],
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
    current_user: Annotated[UserResult, Depends(require_permission("tenant", "delete"))],
):
    """Soft-delete tenant. Path tenant_id must match X-Tenant-ID header. Logs delete action for audit."""
    updated = await tenant_repo.update_tenant(tenant_id, status=TenantStatus.ARCHIVED)
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    settings = get_settings()
    if settings.database_backend == "postgres" and backend.db is not None:
        request_id = getattr(request.state, "request_id", None)
        client_host = request.client.host if request.client else None
        forwarded = request.headers.get("X-Forwarded-For")
        ip_address = (forwarded.split(",")[0].strip() if forwarded else None) or client_host
        user_agent = request.headers.get("User-Agent")
        svc = ApiAuditLogService(backend.db)
        await svc.log_action(
            tenant_id=tenant_id,
            user_id=current_user.id,
            action="delete",
            resource_type="tenants",
            resource_id=tenant_id,
            old_values=None,
            new_values={"status": TenantStatus.ARCHIVED.value},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
            error_message=None,
        )
    return None
