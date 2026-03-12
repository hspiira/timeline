"""Projection ORM models (Phase 5): definition and state."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base


class ProjectionDefinition(Base):
    """Projection definition: name, version, subject_type, watermark (last_event_seq)."""

    __tablename__ = "projection_definition"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            "version",
            name="uq_projection_definition_tenant_name_version",
        ),
        Index(
            "ix_projection_definition_tenant",
            "tenant_id",
            "active",
            postgresql_where=text("active = true"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    subject_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_event_seq: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class ProjectionState(Base):
    """Projection state per subject: JSONB state updated by projection engine."""

    __tablename__ = "projection_state"
    __table_args__ = (
        UniqueConstraint(
            "projection_id",
            "subject_id",
            name="uq_projection_state_projection_subject",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    projection_id: Mapped[str] = mapped_column(
        String, ForeignKey("projection_definition.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subject.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
