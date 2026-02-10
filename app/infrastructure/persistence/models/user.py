"""User ORM model for authentication (tenant-scoped)."""

from sqlalchemy import Boolean, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class User(MultiTenantModel, Base):
    """User model. Table: app_user. Unique (tenant_id, username) and (tenant_id, email)."""

    __tablename__ = "app_user"

    username: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
    )
