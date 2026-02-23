"""DTOs for role use cases (no dependency on ORM)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleResult:
    """Role read-model (result of get_by_id_and_tenant, get_by_tenant, create_role, etc.)."""

    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None
    is_system: bool
    is_active: bool
