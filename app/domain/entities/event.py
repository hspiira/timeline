"""Event domain entity.

Represents the business concept of an event in a timeline, independent of persistence.
Events are immutable (append-only); use a frozen entity.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.domain.exceptions import ValidationException
from app.domain.value_objects.core import EventChain, EventType
from app.shared.utils.datetime import ensure_utc


@dataclass(frozen=True)
class EventEntity:
    """Immutable domain entity for event (SRP: business logic separate from persistence).

    Represents a single event in a subject's timeline with cryptographic
    chain linkage. Validation runs on construction. No mutators.
    """

    id: str
    tenant_id: str
    subject_id: str
    event_type: EventType
    event_time: datetime
    payload: dict[str, Any]
    chain: EventChain

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate event business rules. Raises ValidationException if invalid."""
        if not self.id:
            raise ValidationException("Event ID is required", field="id")
        if not self.tenant_id:
            raise ValidationException("Event must belong to a tenant", field="tenant_id")
        if not self.subject_id:
            raise ValidationException("Event must belong to a subject", field="subject_id")
        now = datetime.now(UTC)
        event_time_utc = ensure_utc(self.event_time)
        if event_time_utc > now:
            raise ValidationException("Event time cannot be in the future", field="event_time")
        if not self.payload:
            raise ValidationException("Event payload cannot be empty", field="payload")

    def is_genesis_event(self) -> bool:
        """Return whether this is the first event in the subject's timeline.

        Returns:
            True if chain has no previous hash.
        """
        return self.chain.is_genesis_event()
