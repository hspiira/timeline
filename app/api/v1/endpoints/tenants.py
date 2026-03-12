"""Tenant API: thin routes delegating to TenantCreationService and tenant repo (Postgres)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_current_user,
    get_tenant_creation_service,
    get_tenant_id,
    get_tenant_repo,
    get_tenant_repo_for_write,
    get_verified_tenant_id,
    get_tenant_integrity_history_repo,
    require_permission,
)
from app.infrastructure.persistence.database import get_db_transactional
from app.application.dtos.user import UserResult
from app.application.interfaces.repositories import ITenantRepository
from app.application.services.tenant_creation_service import TenantCreationService
from app.core.config import get_settings
from app.core.limiter import limit_create_tenant, limit_writes
from app.domain.enums import TenantStatus, IntegrityProfile
from app.infrastructure.services.api_audit_log_service import ApiAuditLogService
from app.shared.request_audit import get_audit_request_context, set_audit_payload
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantIntegrityHistoryItem,
    TenantIntegrityStatus,
    TenantIntegrityUpdateRequest,
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
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
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
        # API audit log: tenant creation has no JWT/tenant header; log in same transaction.
        request_id, ip_address, user_agent = get_audit_request_context(request)
        svc = ApiAuditLogService(db)
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
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
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


@router.get("/integrity", response_model=TenantIntegrityStatus)
async def get_tenant_integrity(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo)],
    history_repo=Depends(get_tenant_integrity_history_repo),
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Return current integrity profile and last change metadata for the current tenant."""
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    latest = await history_repo.get_latest_for_tenant(tenant_id)
    return TenantIntegrityStatus(
        profile=tenant.integrity_profile,
        last_changed_at=latest.changed_at if latest else None,
        cooling_off_ends_at=latest.cooling_off_ends_at if latest else None,
    )


@router.put("/integrity", response_model=TenantIntegrityStatus)
async def update_tenant_integrity(
    request: Request,
    body: TenantIntegrityUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
    history_repo=Depends(get_tenant_integrity_history_repo),
    current_user: Annotated[UserResult, Depends(get_current_user)] = Depends(
        get_current_user
    ),
    _perm: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Change tenant integrity profile and record history."""
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.integrity_profile == body.new_profile:
        latest = await history_repo.get_latest_for_tenant(tenant_id)
        return TenantIntegrityStatus(
            profile=tenant.integrity_profile,
            last_changed_at=latest.changed_at if latest else None,
            cooling_off_ends_at=latest.cooling_off_ends_at if latest else None,
        )

    # For now, changes are effective immediately; effective_from_seq is set to 0.
    previous_profile = tenant.integrity_profile
    updated = await tenant_repo.update_tenant(
        tenant_id, status=None, name=None
    )  # ensure tenant exists; integrity_profile will be set directly below
    orm_tenant = await tenant_repo.get_entity_by_id(tenant_id)
    if orm_tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    orm_tenant.integrity_profile = body.new_profile.value
    await tenant_repo.update_without_audit(orm_tenant)

    await history_repo.create_entry(
        tenant_id=tenant_id,
        previous_profile=previous_profile.value,
        new_profile=body.new_profile.value,
        changed_by_user_id=current_user.id,
        change_reason=body.reason,
        effective_from_seq=0,
        cooling_off_ends_at=None,
    )
    latest = await history_repo.get_latest_for_tenant(tenant_id)
    return TenantIntegrityStatus(
        profile=body.new_profile,
        last_changed_at=latest.changed_at if latest else None,
        cooling_off_ends_at=latest.cooling_off_ends_at if latest else None,
    )


@router.get("/integrity/history", response_model=list[TenantIntegrityHistoryItem])
async def get_tenant_integrity_history(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    history_repo=Depends(get_tenant_integrity_history_repo),
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Return integrity profile change history for the current tenant (most recent first)."""
    rows = await history_repo.list_for_tenant(tenant_id)
    items: list[TenantIntegrityHistoryItem] = []
    for row in rows:
        items.append(
            TenantIntegrityHistoryItem(
                previous_profile=(
                    IntegrityProfile(row.previous_profile)
                    if row.previous_profile is not None
                    else None
                ),
                new_profile=IntegrityProfile(row.new_profile),
                changed_at=row.changed_at,
                changed_by_user_id=row.changed_by_user_id,
                change_reason=row.change_reason,
                cooling_off_ends_at=row.cooling_off_ends_at,
            )
        )
    return items


@router.patch("/{tenant_id}/status", response_model=TenantResponse)
@limit_writes
async def update_tenant_status(
    request: Request,
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    body: TenantStatusUpdate,
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
    _: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
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
    tenant_repo: Annotated[ITenantRepository, Depends(get_tenant_repo_for_write)],
    _: Annotated[object, Depends(require_permission("tenant", "delete"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Soft-delete tenant. Path tenant_id must match X-Tenant-ID header. Logs delete for audit."""
    updated = await tenant_repo.update_tenant(tenant_id, status=TenantStatus.ARCHIVED)
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    set_audit_payload(request, new_values={"status": TenantStatus.ARCHIVED.value})
    return None
