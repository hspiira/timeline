"""Event transition rule API schemas."""

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


class EventTransitionRuleUpdate(BaseModel):
    """Request body for PATCH (partial update)."""

    required_prior_event_types: list[str] | None = Field(
        default=None,
        min_length=1,
        description="Replace the list of required prior event types.",
    )
    description: str | None = Field(default=None, max_length=500)


class EventTransitionRuleResponse(BaseModel):
    """Event transition rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    event_type: str
    required_prior_event_types: list[str]
    description: str | None
