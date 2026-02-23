"""Flow and FlowSubject ORM models. Flow = workflow instance grouping many subjects."""

from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class Flow(MultiTenantModel, Base):
    """Flow: named instance of a workflow grouping many subjects. Table: flow."""

    __tablename__ = "flow"

    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    workflow_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("workflow.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hierarchy_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # {"1": "Renewals", "2": "2026", "3": "2026-03-Acme"}


class FlowSubject(Base):
    """Junction: subject belongs to a flow. Table: flow_subject."""

    __tablename__ = "flow_subject"

    flow_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("flow.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    subject_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("subject.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_flow_subject_flow_id", "flow_id"),
        Index("ix_flow_subject_subject_id", "subject_id"),
        UniqueConstraint("flow_id", "subject_id", name="uq_flow_subject_flow_subject"),
    )
