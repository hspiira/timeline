"""SQLAlchemy mixins for common model patterns (DRY).

Provides: CuidMixin, TenantMixin, TimestampMixin, SoftDeleteMixin,
UserAuditMixin, VersionedMixin, FullAuditMixin, and combined
MultiTenantModel, AuditedMultiTenantModel, FullyAuditedMultiTenantModel.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func

from app.shared.utils.generators import generate_cuid


class CuidMixin:
    """Mixin for models using CUID as primary key. Provides id with default generate_cuid."""

    @declared_attr
    def id(cls) -> Mapped[str]:
        return mapped_column(String, primary_key=True, default=generate_cuid)


class TenantMixin:
    """Mixin for multi-tenant models. Provides tenant_id FK to tenant with CASCADE delete."""

    @declared_attr
    def tenant_id(cls) -> Mapped[str]:
        return mapped_column(
            String,
            ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class TimestampMixin:
    """Mixin for created_at and updated_at (server defaults, timezone-aware)."""

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )


class SoftDeleteMixin:
    """Mixin for soft delete (deleted_at). Null means not deleted."""

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(DateTime(timezone=True), nullable=True, index=True)


class UserAuditMixin(TimestampMixin, SoftDeleteMixin):
    """Mixin for user audit: created_by, updated_by, deleted_by (FK to user.id)."""

    @declared_attr
    def created_by(cls) -> Mapped[str | None]:
        return mapped_column(
            String,
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )

    @declared_attr
    def updated_by(cls) -> Mapped[str | None]:
        return mapped_column(
            String, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
        )

    @declared_attr
    def deleted_by(cls) -> Mapped[str | None]:
        return mapped_column(
            String, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
        )


class VersionedMixin:
    """Mixin for optimistic locking: version integer, default 1."""

    @declared_attr
    def version(cls) -> Mapped[int]:
        return mapped_column(Integer, default=1, nullable=False)


class FullAuditMixin(UserAuditMixin, VersionedMixin):
    """Mixin for full audit: timestamps, user tracking, version, audit_metadata JSON."""

    @declared_attr
    def audit_metadata(cls) -> Mapped[dict[str, Any] | None]:
        return mapped_column(JSON, nullable=True)


class MultiTenantModel(CuidMixin, TenantMixin, TimestampMixin):
    """Combined mixin: CUID + tenant_id + created_at/updated_at. Common for Timeline models."""

    __abstract__ = True


class AuditedMultiTenantModel(CuidMixin, TenantMixin, UserAuditMixin):
    """Combined mixin: CUID + tenant_id + user audit (timestamps, created_by, etc.)."""

    __abstract__ = True


class FullyAuditedMultiTenantModel(CuidMixin, TenantMixin, FullAuditMixin):
    """Combined mixin: CUID + tenant_id + full audit (version, audit_metadata)."""

    __abstract__ = True
