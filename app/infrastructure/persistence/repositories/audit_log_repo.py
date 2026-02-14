"""Audit log repository. Append-only; implements IAuditLogRepository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.audit_log import AuditLogEntryCreate, AuditLogResult
from app.infrastructure.persistence.models.audit_log import AuditLog
from app.shared.utils.generators import generate_cuid


def _orm_to_result(row: AuditLog) -> AuditLogResult:
    """Map ORM to application DTO."""
    return AuditLogResult(
        id=row.id,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        old_values=row.old_values,
        new_values=row.new_values,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        request_id=row.request_id,
        timestamp=row.timestamp,
        success=row.success,
        error_message=row.error_message,
    )


class AuditLogRepository:
    """Append-only audit log repository. No update/delete."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entry: AuditLogEntryCreate) -> AuditLogResult:
        """Append one audit log entry; return created record."""
        row = AuditLog(
            id=generate_cuid(),
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            old_values=entry.old_values,
            new_values=entry.new_values,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
            request_id=entry.request_id,
            success=entry.success,
            error_message=entry.error_message,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return _orm_to_result(row)

    async def list(
        self,
        tenant_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        resource_type: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ) -> list[AuditLogResult]:
        """List audit log entries for tenant with optional filters (newest first)."""
        conditions = [AuditLog.tenant_id == tenant_id]
        if resource_type is not None:
            conditions.append(AuditLog.resource_type == resource_type)
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if from_timestamp is not None:
            conditions.append(AuditLog.timestamp >= from_timestamp)
        if to_timestamp is not None:
            conditions.append(AuditLog.timestamp <= to_timestamp)

        stmt = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [_orm_to_result(r) for r in result.scalars().all()]
