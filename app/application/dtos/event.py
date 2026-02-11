"""DTOs for event use cases (no dependency on ORM or presentation schemas)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CreateEventCommand:
    """Application-layer input for creating one event. Presentation layer maps to this."""

    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]


@dataclass
class EventResult:
    """Event read-model (result of get_by_id, get_last_event, create_event, etc.)."""

    id: str
    tenant_id: str
    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]
    previous_hash: str | None
    hash: str


@dataclass(frozen=True)
class EventToPersist:
    """Event data ready for bulk persist (hash and previous_hash already computed)."""

    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]
    hash: str
    previous_hash: str | None
