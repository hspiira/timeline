"""DTOs for tenant use cases (no dependency on ORM)."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import TenantStatus


@dataclass(frozen=True)
class TenantCreationResult:
    """Result of tenant creation (new tenant + admin user + RBAC). Admin password is never included.

    When C2 flow is used (Postgres + set_password_base_url), set_password_url and
    set_password_expires_at are set; otherwise they are None.
    """

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str
    admin_email: str
    # Raw token for building set_password_url (endpoint adds base URL). None when token store not used.
    set_password_token: str | None = None
    set_password_expires_at: datetime | None = None


@dataclass(frozen=True)
class TenantResult:
    """Tenant read-model (result of get_by_id, get_by_code, create_tenant, etc.)."""

    id: str
    code: str
    name: str
    status: TenantStatus
