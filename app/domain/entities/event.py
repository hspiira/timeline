"""Event domain entity.

Represents the business concept of an event in a timeline, independent of persistence.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.domain.value_objects.core import EventChain, EventType
from app.shared.utils.datetime import ensure_utc


@dataclass
class EventEntity:
    """Domain entity for event (SRP: business logic separate from persistence).

    Represents a single event in a subject's timeline with cryptographic
    chain linkage. Validation (e.g. no future event_time) is done here.
    """

    id: str
    tenant_id: str
    subject_id: str
    event_type: EventType
    event_time: datetime
    payload: dict[str, Any]
    chain: EventChain

    def validate(self) -> bool:
        """Validate event business rules.

        Ensures identity fields are set, event time is not in the future, and
        payload is non-empty. Chain integrity is enforced at EventChain
        construction time.

        Returns:
            True if valid.

        Raises:
            ValueError: If id, tenant_id, or subject_id is missing; event_time
                is in the future; or payload is empty.
        """
        if not self.id:
            raise ValueError("Event ID is required")
        if not self.tenant_id:
            raise ValueError("Event must belong to a tenant")
        if not self.subject_id:
            raise ValueError("Event must belong to a subject")
        now = datetime.now(UTC)
        event_time = ensure_utc(self.event_time)
        if event_time > now:
            raise ValueError("Event time cannot be in the future")
        if not self.payload:
            raise ValueError("Event payload cannot be empty")
        return True

    def is_genesis_event(self) -> bool:
        """Return whether this is the first event in the subject's timeline.

        Returns:
            True if chain has no previous hash.
        """
        return self.chain.is_genesis_event()
