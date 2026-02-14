"""API audit log service: writes to audit_log table (SOC 2 compliance)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.audit_log import AuditLogEntryCreate
from app.infrastructure.persistence.repositories.audit_log_repo import AuditLogRepository

if TYPE_CHECKING:
    pass


class ApiAuditLogService:
    """Logs API actions to audit_log table. Use from middleware or use cases."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = AuditLogRepository(db)

    async def log_action(
        self,
        tenant_id: str,
        user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Append one audit log entry."""
        entry = AuditLogEntryCreate(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=success,
            error_message=error_message,
        )
        await self._repo.create(entry)
