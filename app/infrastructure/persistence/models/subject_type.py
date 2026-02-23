"""SubjectType ORM model. Tenant-defined subject type configuration with optional JSON schema."""

from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class SubjectType(MultiTenantModel, Base):
    """Subject type configuration. Table: subject_type. Unique (tenant_id, type_name)."""

    __tablename__ = "subject_type"

    type_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_timeline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_event_types: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "type_name", name="uq_subject_type_tenant_type"),
    )
