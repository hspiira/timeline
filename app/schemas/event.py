"""Event API schemas. Minimal for Phase 3; full validation in Phase 6."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


def _ensure_aware_datetime(v: datetime | str) -> datetime:
    """Accept datetime or ISO string; treat naive datetimes as UTC (common from frontends)."""
    if isinstance(v, str):
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    else:
        dt = v
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class EventCreateRequest(BaseModel):
    """Payload for creating an event. Schema version must match an active schema."""

    subject_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    schema_version: int = Field(..., ge=1)
    event_time: AwareDatetime
    payload: dict[str, Any] = Field(default_factory=dict)
    workflow_instance_id: str | None = None
    correlation_id: str | None = None

    @field_validator("event_time", mode="before")
    @classmethod
    def event_time_aware(cls, v: Any) -> datetime:
        if v is None:
            raise ValueError("event_time is required")
        return _ensure_aware_datetime(v)


class EventListResponse(BaseModel):
    """Event list item (list endpoint)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    event_type: str
    event_time: AwareDatetime
    workflow_instance_id: str | None = None
    correlation_id: str | None = None


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
    workflow_instance_id: str | None = None
    correlation_id: str | None = None


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


class VerificationJobStartedResponse(BaseModel):
    """Response when a background verification job is started (202)."""

    job_id: str
    message: str = "Verification job started; poll GET /events/verify/tenant/jobs/{job_id} for status."


class VerificationJobStatusResponse(BaseModel):
    """Status of a background verification job."""

    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: ChainVerificationResponse | None = None
    error: str | None = None
    total_events: int | None = None
