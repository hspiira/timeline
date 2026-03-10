"""Audit log ORM model. Append-only API action log for compliance (SOC 2)."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Connection, DateTime, ForeignKey, String, Text, event, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.infrastructure.persistence.database import Base
from app.shared.utils.generators import generate_cuid


class AuditLog(Base):
    """API audit log entry. Who did what, when, to which resource. No update/delete."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_cuid)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


@event.listens_for(AuditLog, "before_update")
def _prevent_audit_log_updates(
    _mapper: Mapper[Any], _connection: Connection, _target: AuditLog
) -> None:
    """Audit log entries are append-only; updates are forbidden."""
    raise ValueError(
        "Audit log entries are immutable and cannot be updated."
    )


@event.listens_for(AuditLog, "before_delete")
def _prevent_audit_log_deletes(
    _mapper: Mapper[Any], _connection: Connection, _target: AuditLog
) -> None:
    """Audit log entries cannot be deleted for compliance."""
    raise ValueError(
        "Audit log entries cannot be deleted."
    )
