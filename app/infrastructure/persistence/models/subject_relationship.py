"""SubjectRelationship ORM model. Links two subjects with a relationship kind."""

from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class SubjectRelationship(MultiTenantModel, Base):
    """Subject-to-subject relationship. Table: subject_relationship.

    Unique (tenant_id, source_subject_id, target_subject_id, relationship_kind).
    """

    __tablename__ = "subject_relationship"

    source_subject_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_subject_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_kind: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_subject_id",
            "target_subject_id",
            "relationship_kind",
            name="uq_subject_relationship_tenant_source_target_kind",
        ),
        Index(
            "ix_subject_relationship_source_kind",
            "source_subject_id",
            "relationship_kind",
        ),
        Index(
            "ix_subject_relationship_target_kind",
            "target_subject_id",
            "relationship_kind",
        ),
    )
