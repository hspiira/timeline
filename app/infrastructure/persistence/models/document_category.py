"""DocumentCategory ORM model. Tenant-defined document category with optional metadata schema."""

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class DocumentCategory(MultiTenantModel, Base):
    """Document category configuration. Table: document_category. Unique (tenant_id, category_name)."""

    __tablename__ = "document_category"

    category_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    default_retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "category_name", name="uq_document_category_tenant_name"
        ),
    )
