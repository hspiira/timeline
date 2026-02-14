"""DTOs for subject snapshot (state checkpoint)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SubjectSnapshotResult:
    """Subject snapshot read-model (get_latest_by_subject)."""

    id: str
    subject_id: str
    tenant_id: str
    snapshot_at_event_id: str
    state_json: dict[str, Any]
    event_count_at_snapshot: int
    created_at: datetime
