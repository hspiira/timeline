"""Audit log and API audit dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import (
    get_db,
    get_db_transactional,
)
from app.infrastructure.persistence.repositories import AuditLogRepository
from app.infrastructure.services.api_audit_log_service import ApiAuditLogService
from app.shared.request_audit import (
    get_audit_action_from_method,
    get_audit_request_context,
    get_audit_resource_from_path,
    get_tenant_and_user_for_audit,
)

async def get_audit_log_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogRepository:
    """Audit log repository for read (list). Writes are via ensure_audit_logged (same transaction)."""
    return AuditLogRepository(db)


async def ensure_audit_logged(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> AsyncIterator[None]:
    """Dependency that writes API audit log in the same transaction when the route returns normally.

    Add to write endpoints (POST/PUT/PATCH/DELETE) so the audit row is committed
    in the same transaction as the mutation. If the route raises, the transaction
    rolls back and no audit row is written.
    """
    yield
    # After route returned normally: write audit in same transaction before commit.
    tenant_id, user_id = get_tenant_and_user_for_audit(request)
    if not tenant_id:
        return
    resource_type, resource_id = get_audit_resource_from_path(request.url.path)
    if not resource_type:
        return
    request_id, ip_address, user_agent = get_audit_request_context(request)
    action = get_audit_action_from_method(request.method)
    try:
        svc = ApiAuditLogService(db)
        await svc.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=None,
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
            error_message=None,
        )
    except Exception:
        raise
