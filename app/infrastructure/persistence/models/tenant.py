"""Tenant ORM model. Root entity for multi-tenant hierarchy (no tenant_id)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import TenantStatus
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin, TimestampMixin


class Tenant(CuidMixin, TimestampMixin, Base):
    """Root tenant entity. Table: tenant. Status: active, suspended, archived."""

    __tablename__ = "tenant"

    code: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=TenantStatus.ACTIVE.value, index=True
    )
    integrity_profile: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="Standard"
    )
    profile_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    profile_changed_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("app_user.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ({})".format(
                ", ".join(
                    "'{}'".format(v.replace("'", "''"))
                    for v in TenantStatus.values()
                )
            ),
            name="tenant_status_check",
        ),
        CheckConstraint(
            "integrity_profile IN ('Standard','Compliance','Legal Grade')",
            name="chk_integrity_profile",
        ),
    )
