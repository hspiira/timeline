"""DTOs for event schema use cases (no dependency on ORM)."""

from dataclasses import dataclass
from typing import Any

from app.domain.value_objects.core import EventType


@dataclass(frozen=True)
class EventSchemaResult:
    """Event schema read-model (result of get_by_id, get_by_version, get_active_schema, etc.)."""

    id: str
    tenant_id: str
    event_type: EventType
    schema_definition: dict[str, Any]
    version: int
    is_active: bool
    created_by: str | None
