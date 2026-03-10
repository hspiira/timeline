"""DTOs for event use cases (no dependency on ORM or presentation schemas)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.shared.utils.datetime import parse_aware_datetime


class EventCreate(BaseModel):
    """Payload for creating an event (request body and use-case input)."""

    subject_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    schema_version: int = Field(..., ge=1)
    event_time: datetime = Field(...)
    payload: dict[str, Any] = Field(default_factory=dict)
    workflow_instance_id: str | None = None
    correlation_id: str | None = None

    @field_validator("event_time", mode="before")
    @classmethod
    def event_time_aware(cls, v: Any) -> datetime:
        if v is None:
            raise ValueError("event_time is required")
        return parse_aware_datetime(v)


@dataclass(frozen=True)
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
    workflow_instance_id: str | None = None
    correlation_id: str | None = None


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
    workflow_instance_id: str | None = None
    correlation_id: str | None = None
