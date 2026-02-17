"""Tenant API schemas."""

from pydantic import BaseModel, Field, SecretStr, field_validator

from app.domain.enums import TenantStatus


def _normalize_tenant_code(value: str) -> str:
    """Lowercase, no spaces, join with '-' (e.g. 'My Org' -> 'my-org')."""
    return "-".join(value.strip().lower().split())


class TenantCreateRequest(BaseModel):
    """Request body for creating a new tenant with admin user.

    Code and name are required. Optionally provide admin_initial_password
    (min 8 chars); if not provided, a password is generated but not returned
    (admin must use password reset or another flow for first access).
    Tenant code is normalized: lowercase, spaces replaced with '-'.
    """

    code: str = Field(
        ...,
        min_length=3,
        max_length=15,
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        description="Unique tenant code (normalized to lowercase, hyphen-separated slug)",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    admin_initial_password: SecretStr | None = Field(
        default=None,
        description="Optional initial admin password (min 8 chars); if set, used and never returned in response",
    )

    @field_validator("admin_initial_password")
    @classmethod
    def validate_admin_password_length(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and len(v.get_secret_value()) < 8:
            raise ValueError("admin_initial_password must be at least 8 characters")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        """Normalize before pattern/length checks so e.g. 'My Org' becomes 'my-org'."""
        return _normalize_tenant_code(v)


class TenantCreateResponse(BaseModel):
    """Response after tenant creation. Admin password is never returned (use admin_initial_password in request or password reset)."""

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str


class TenantUpdate(BaseModel):
    """Request body for updating a tenant (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: TenantStatus | None = None


class TenantStatusUpdate(BaseModel):
    """Request body for PATCH /tenants/{id}/status."""

    new_status: TenantStatus


class TenantResponse(BaseModel):
    """Tenant in list/get responses."""

    id: str
    code: str
    name: str
    status: TenantStatus
