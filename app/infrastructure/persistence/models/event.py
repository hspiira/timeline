"""Event ORM model. Append-only event sourcing; immutable after creation."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Connection,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Mapper, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin, TenantMixin


class Event(CuidMixin, TenantMixin, Base):
    """Immutable event entity. Table: event. Hash chain and payload; no updated_at."""

    __tablename__ = "event"

    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subject.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_event_subject_time", "subject_id", "event_time"),
        Index("ix_event_tenant_subject", "tenant_id", "subject_id"),
        Index(
            "ix_event_tenant_type_version", "tenant_id", "event_type", "schema_version"
        ),
        CheckConstraint("created_at IS NOT NULL", name="ck_event_created_at_immutable"),
    )


@event.listens_for(Event, "before_update")
def _prevent_event_updates(
    _mapper: Mapper[Any], _connection: Connection, _target: Event
) -> None:
    """Events are append-only; updates are forbidden."""
    raise ValueError(
        "Events are immutable and cannot be updated. "
        "Create a new compensating event instead."
    )
