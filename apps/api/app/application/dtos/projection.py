"""DTOs for projection use cases (read-models; no ORM dependency)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProjectionDefinitionResult:
    """Projection definition read-model (list, get, create)."""

    id: str
    tenant_id: str
    name: str
    version: int
    subject_type: str | None
    last_event_seq: int
    active: bool
    created_at: datetime


@dataclass(frozen=True)
class ProjectionStateResult:
    """Projection state read-model (per subject)."""

    id: str
    projection_id: str
    subject_id: str
    state: dict
    updated_at: datetime
