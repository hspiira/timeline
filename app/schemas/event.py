"""Event API schemas. Minimal for Phase 3; full validation in Phase 6."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    """Payload for creating an event. Schema version must match an active schema."""

    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]


class EventListResponse(BaseModel):
    """Event list item (list endpoint)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    event_type: str
    event_time: datetime


class EventResponse(BaseModel):
    """Event detail (get endpoint) and create response shape."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    payload: dict[str, Any]
    hash: str
