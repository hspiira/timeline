"""Tenant API schemas."""

from pydantic import BaseModel, Field, SecretStr, field_serializer, field_validator

from app.domain.enums import TenantStatus


def _normalize_tenant_code(value: str) -> str:
    """Lowercase, no spaces, join with '-' (e.g. 'My Org' -> 'my-org')."""
    return "-".join(value.strip().lower().split())


class TenantCreateRequest(BaseModel):
    """Request body for creating a new tenant with admin user.

    Only name and tenant code are required. Admin password is auto-generated
    and returned in the response. Tenant code is normalized: lowercase,
    spaces replaced with '-'.
    """

    code: str = Field(
        ...,
        min_length=3,
        max_length=15,
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        description="Unique tenant code (normalized to lowercase, hyphen-separated slug)",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        """Normalize before pattern/length checks so e.g. 'My Org' becomes 'my-org'."""
        return _normalize_tenant_code(v)


class TenantCreateResponse(BaseModel):
    """Response after tenant creation. Includes generated admin password (show once, then change)."""

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str
    admin_password: SecretStr = Field(..., description="Auto-generated; show once to the user")

    @field_serializer("admin_password", when_used="json")
    def _serialize_admin_password(self, v: SecretStr) -> str:
        return v.get_secret_value()


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
