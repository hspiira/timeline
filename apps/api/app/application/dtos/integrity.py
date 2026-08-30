"""DTOs for chain integrity (epochs, profiles)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OpenEpochAssignment:
    """Result of get-or-create open epoch: id, profile snapshot, and current event count.

    event_count is used to set first_event_seq on the epoch when the first event is appended.
    """

    epoch_id: str
    profile_snapshot: str
    event_count: int
