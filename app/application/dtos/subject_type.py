"""DTOs for subject type configuration (no dependency on ORM)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SubjectTypeResult:
    """Subject type read-model (result of get_by_id, get_by_tenant_and_type, etc.)."""

    id: str
    tenant_id: str
    type_name: str
    display_name: str
    description: str | None
    schema: dict[str, Any] | None
    version: int
    is_active: bool
    icon: str | None
    color: str | None
    has_timeline: bool
    allow_documents: bool
    created_by: str | None
