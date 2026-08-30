"""DTOs for event transition rule use cases."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EventTransitionRuleResult:
    """Read-model for a single event transition rule."""

    id: str
    tenant_id: str
    event_type: str
    required_prior_event_types: list[str]
    description: str | None
    prior_event_payload_conditions: dict[str, dict[str, Any]] | None = None
    max_occurrences_per_stream: int | None = None
    fresh_prior_event_type: str | None = None
