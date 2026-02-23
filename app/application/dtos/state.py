"""DTOs for state derivation (event replay result)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StateResult:
    """Derived state from replaying events for a subject (get_current_state)."""

    state: dict[str, Any]
    last_event_id: str | None
    event_count: int
