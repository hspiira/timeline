"""EventTransitionRule ORM model. Transition validation: required prior event types per event_type."""

from typing import Any

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class EventTransitionRule(MultiTenantModel, Base):
    """Event transition rule. Table: event_transition_rule. Unique (tenant_id, event_type)."""

    __tablename__ = "event_transition_rule"

    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    required_prior_event_types: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prior_event_payload_conditions: Mapped[dict[str, dict[str, Any]] | None] = (
        mapped_column(JSONB, nullable=True)
    )
    max_occurrences_per_stream: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    fresh_prior_event_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "event_type",
            name="uq_event_transition_rule_tenant_event_type",
        ),
    )
