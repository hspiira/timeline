"""Event API schemas. Minimal for Phase 3; full validation in Phase 6."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventCreate(BaseModel):
    """Payload for creating an event. Schema version must match an active schema."""

    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]
