"""Audit log API: list tenant-scoped audit entries (who did what, when)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_audit_log_repo, get_tenant_id, require_permission
from app.application.interfaces.repositories import IAuditLogRepository
from app.schemas.audit_log import AuditLogEntryResponse, AuditLogListResponse

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_log(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_repo: Annotated[IAuditLogRepository, Depends(get_audit_log_repo)],
    _: Annotated[object, Depends(require_permission("audit", "read"))] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    user_id: str | None = Query(None, description="Filter by user id"),
    from_timestamp: datetime | None = Query(None, description="From (inclusive) ISO8601"),
    to_timestamp: datetime | None = Query(None, description="To (inclusive) ISO8601"),
):
    """List audit log entries for the tenant (paginated, optional filters)."""
    items, total = await audit_repo.list_with_count(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        resource_type=resource_type,
        user_id=user_id,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )
    return AuditLogListResponse(
        items=[AuditLogEntryResponse.model_validate(e) for e in items],
        skip=skip,
        limit=limit,
        total=total,
    )
