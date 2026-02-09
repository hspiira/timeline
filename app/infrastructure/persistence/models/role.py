"""Role ORM model. Tenant-scoped roles (admin, auditor, agent)."""

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class Role(MultiTenantModel, Base):
    """Role. Table: role. Unique (tenant_id, code)."""

    __tablename__ = "role"

    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_role_tenant_code"),)
