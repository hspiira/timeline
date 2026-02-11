"""DTOs for tenant use cases (no dependency on ORM)."""

from dataclasses import dataclass

from app.domain.enums import TenantStatus


@dataclass(frozen=True)
class TenantCreationResult:
    """Result of tenant creation (new tenant + admin user + RBAC)."""

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str
    admin_password: str


@dataclass(frozen=True)
class TenantResult:
    """Tenant read-model (result of get_by_id, get_by_code, create_tenant, etc.)."""

    id: str
    code: str
    name: str
    status: TenantStatus
