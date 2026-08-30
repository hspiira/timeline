"""DTOs for relationship kind (no dependency on ORM)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RelationshipKindResult:
    """Relationship kind read-model (result of list, get)."""

    id: str
    tenant_id: str
    kind: str
    display_name: str
    description: str | None
    payload_schema: dict[str, Any] | None
