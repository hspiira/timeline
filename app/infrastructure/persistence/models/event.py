"""Event ORM model. Append-only event sourcing; immutable after creation."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Connection,
    DateTime,
    Enum as SaEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Mapper, mapped_column
from sqlalchemy.sql import func

from app.domain.enums import EventIntegrityStatus
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
    epoch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("integrity_epoch.id"), nullable=True
    )
    integrity_status: Mapped[EventIntegrityStatus] = mapped_column(
        SaEnum(EventIntegrityStatus, create_constraint=False),
        nullable=False,
        server_default=EventIntegrityStatus.VALID.value,
    )
    tsa_anchor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tsa_anchor.id"), nullable=True
    )
    merkle_leaf_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_instance_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Monotonic insertion order (sequence); use for ORDER BY instead of created_at (transaction-scoped).
    event_seq: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("nextval('event_event_seq_seq'::regclass)"),
    )
    # Platform: idempotency key for connectors (CDC/Kafka retries); optional for API.
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Platform: originating system identifier (e.g. "api:crm", "cdc:postgres:policies").
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_event_subject_time", "subject_id", "event_time"),
        Index(
            "ix_event_subject_external_id",
            "subject_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "ix_event_tenant_source",
            "tenant_id",
            "source",
            postgresql_where=text("source IS NOT NULL"),
        ),
        Index("ix_event_tenant_subject", "tenant_id", "subject_id"),
        Index(
            "ix_event_tenant_subject_workflow",
            "tenant_id",
            "subject_id",
            "workflow_instance_id",
            postgresql_where=text("workflow_instance_id IS NOT NULL"),
        ),
        Index(
            "ix_event_tenant_type_version", "tenant_id", "event_type", "schema_version"
        ),
        Index(
            "ix_event_tenant_created_at",
            "tenant_id",
            "created_at",
            "event_time",
            "id",
        ),
        Index("ix_event_tenant_event_seq", "tenant_id", "event_seq"),
        Index("idx_events_epoch", "epoch_id"),
        Index(
            "idx_events_integrity",
            "tenant_id",
            "integrity_status",
            postgresql_where=text(
                "integrity_status <> 'Valid'"
            ),
        ),
        CheckConstraint("created_at IS NOT NULL", name="ck_event_created_at_immutable"),
        CheckConstraint(
            "integrity_status IN "
            "('Valid','Chain Break','Repaired','Erased','Pending Anchor')",
            name="chk_event_integrity_status",
        ),
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


@event.listens_for(Event, "before_delete")
def _prevent_event_deletes(
    _mapper: Mapper[Any], _connection: Connection, _target: Event
) -> None:
    """Events are append-only; deletions are forbidden for chain integrity."""
    raise ValueError(
        "Events are immutable and cannot be deleted. "
        "Create a new compensating event instead."
    )
