"""Tenant integrity profile history ORM model.

Append-only log of integrity profile changes per tenant.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin


class TenantIntegrityProfileHistory(CuidMixin, Base):
    """History of integrity profile changes for a tenant. Table: tenant_integrity_profile_history."""

    __tablename__ = "tenant_integrity_profile_history"

    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_profile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_profile: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    changed_by_user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cooling_off_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

