"""DTOs for event use cases (no dependency on ORM)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class EventToPersist:
    """Event data ready for bulk persist (hash and previous_hash already computed)."""

    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]
    hash: str
    previous_hash: str | None
