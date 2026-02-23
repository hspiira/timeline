"""DTOs for document category configuration (no dependency on ORM)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentCategoryResult:
    """Document category read-model (result of get_by_id, get_by_tenant_and_name, etc.)."""

    id: str
    tenant_id: str
    category_name: str
    display_name: str
    description: str | None
    metadata_schema: dict[str, Any] | None
    default_retention_days: int | None
    is_active: bool
    created_by: str | None
