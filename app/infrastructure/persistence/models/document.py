"""Document ORM model. File storage metadata and versioning."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class Document(MultiTenantModel, Base):
    """Document entity. Table: document. Links to subject and optional event."""

    __tablename__ = "document"

    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subject.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("event.id"), nullable=True, index=True
    )
    document_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String, nullable=False, index=True)
    storage_ref: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_document_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("document.id"), nullable=True
    )
    is_latest_version: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_document_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_document_checksum_unique", "tenant_id", "checksum", unique=True),
        Index(
            "ux_document_versions",
            "tenant_id",
            "subject_id",
            "parent_document_id",
            "version",
            unique=True,
        ),
        # Root documents (parent_document_id IS NULL): one version=1 per (tenant, subject).
        Index(
            "ux_document_root_version",
            "tenant_id",
            "subject_id",
            "version",
            unique=True,
            postgresql_where=text("parent_document_id IS NULL"),
        ),
    )
