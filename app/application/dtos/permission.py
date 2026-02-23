"""DTOs for permission use cases (no dependency on ORM)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionResult:
    """Permission read-model (result of get_by_code_and_tenant, create_permission, etc.)."""

    id: str
    tenant_id: str
    code: str
    resource: str
    action: str
    description: str | None
