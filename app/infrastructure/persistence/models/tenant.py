"""Tenant ORM model. Root entity for multi-tenant hierarchy (no tenant_id)."""

from sqlalchemy import CheckConstraint, String
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
    )
