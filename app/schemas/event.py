"""Event API schemas. Minimal for Phase 3; full validation in Phase 6."""

from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict


class EventCreateRequest(BaseModel):
    """Payload for creating an event. Schema version must match an active schema."""

    subject_id: str
    event_type: str
    schema_version: int
    event_time: AwareDatetime
    payload: dict[str, Any]


class EventListResponse(BaseModel):
    """Event list item (list endpoint)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    event_type: str
    event_time: AwareDatetime


class EventResponse(BaseModel):
    """Event detail (get endpoint) and create response shape."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    event_type: str
    schema_version: int
    event_time: AwareDatetime
    payload: dict[str, Any]
    hash: str


class EventVerificationResult(BaseModel):
    """Result of verifying a single event (hash + chain)."""

    event_id: str
    event_type: str
    event_time: AwareDatetime
    sequence: int
    is_valid: bool
    error_type: str | None = None
    error_message: str | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None


class EventCountResponse(BaseModel):
    """Response for GET /count (total events for tenant)."""

    total: int


class ChainVerificationResponse(BaseModel):
    """Result of verifying a subject or tenant event chain."""

    subject_id: str | None
    tenant_id: str
    total_events: int
    valid_events: int
    invalid_events: int
    is_chain_valid: bool
    verified_at: AwareDatetime
    event_results: list[EventVerificationResult] = []
