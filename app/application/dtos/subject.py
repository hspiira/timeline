"""DTOs for subject use cases (no dependency on ORM)."""

from dataclasses import dataclass
from typing import Any

from app.domain.value_objects.core import SubjectType


@dataclass(frozen=True)
class SubjectResult:
    """Subject read-model (result of get_by_id, get_by_id_and_tenant, create_subject, etc.)."""

    id: str
    tenant_id: str
    subject_type: SubjectType
    external_ref: str | None
    display_name: str
    attributes: dict[str, Any]
