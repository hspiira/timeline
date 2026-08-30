"""DTOs for subject relationship use cases (no dependency on ORM)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SubjectRelationshipResult:
    """Subject relationship read-model (result of create, list, etc.)."""

    id: str
    tenant_id: str
    source_subject_id: str
    target_subject_id: str
    relationship_kind: str
    payload: dict[str, Any] | None
    created_at: datetime
