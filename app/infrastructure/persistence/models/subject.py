"""Subject ORM model. Entity whose timeline (event chain) is maintained."""

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class Subject(MultiTenantModel, Base):
    """Subject entity. Table: subject. Index: (tenant_id, subject_type)."""

    __tablename__ = "subject"

    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    external_ref: Mapped[str | None] = mapped_column(String, index=True)

    __table_args__ = (Index("ix_subject_tenant_type", "tenant_id", "subject_type"),)
