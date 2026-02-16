"""DTOs for event transition rule use cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EventTransitionRuleResult:
    """Read-model for a single event transition rule."""

    id: str
    tenant_id: str
    event_type: str
    required_prior_event_types: list[str]
    description: str | None
