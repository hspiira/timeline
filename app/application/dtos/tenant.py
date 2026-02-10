"""DTOs for tenant use cases (no dependency on ORM)."""

from dataclasses import dataclass


@dataclass
class TenantResult:
    """Tenant read-model (result of get_by_id, get_by_code, create_tenant, etc.)."""

    id: str
    code: str
    name: str
    status: str
