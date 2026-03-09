"""Event API schemas. Minimal for Phase 3; full validation in Phase 6."""

from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

# Request body for create event: use application DTO (single source of truth).
from app.application.dtos.event import EventCreate


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
