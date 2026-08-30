"""Event transition rule API schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventTransitionRuleCreateRequest(BaseModel):
    """Request body for creating an event transition rule."""

    event_type: str = Field(..., min_length=1, max_length=128)
    required_prior_event_types: list[str] = Field(
        ...,
        min_length=1,
        description="All of these event types must have occurred in the stream before the event_type can be emitted.",
    )
    description: str | None = Field(default=None, max_length=500)
    prior_event_payload_conditions: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="Optional payload conditions per prior event type (last occurrence must match).",
    )
    max_occurrences_per_stream: int | None = Field(
        default=None,
        ge=1,
        description="Max times this event type may appear in the stream.",
    )
    fresh_prior_event_type: str | None = Field(
        default=None,
        max_length=128,
        description="Require a new prior event of this type after the last emission of the current type.",
    )


class EventTransitionRuleUpdate(BaseModel):
    """Request body for PATCH (partial update)."""

    required_prior_event_types: list[str] | None = Field(
        default=None,
        min_length=1,
        description="Replace the list of required prior event types.",
    )
    description: str | None = Field(default=None, max_length=500)
    prior_event_payload_conditions: dict[str, dict[str, Any]] | None = Field(
        default=None,
    )
    max_occurrences_per_stream: int | None = Field(default=None, ge=1)
    fresh_prior_event_type: str | None = Field(default=None, max_length=128)


class EventTransitionRuleResponse(BaseModel):
    """Event transition rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    event_type: str
    required_prior_event_types: list[str]
    description: str | None
    prior_event_payload_conditions: dict[str, dict[str, Any]] | None = None
    max_occurrences_per_stream: int | None = None
    fresh_prior_event_type: str | None = None
