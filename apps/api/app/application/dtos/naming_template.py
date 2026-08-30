"""DTOs for naming template configuration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NamingTemplateResult:
    """Naming template read-model."""

    id: str
    tenant_id: str
    scope_type: str  # flow | subject | document
    scope_id: str
    template_string: str
    placeholders: list[dict[str, Any]] | None
