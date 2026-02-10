"""Tenant API schemas."""

from pydantic import BaseModel, Field

from app.domain.enums import TenantStatus


class TenantCreateRequest(BaseModel):
    """Request body for creating a new tenant with admin user."""

    code: str = Field(
        ..., min_length=1, max_length=64, description="Unique tenant code"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    admin_password: str | None = Field(
        default=None,
        min_length=8,
        description="Admin user password; generated if omitted",
    )


class TenantCreateResponse(BaseModel):
    """Response after tenant creation. Admin password is never serialized in API output."""

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str
    admin_password: str = Field(..., exclude=True)


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
    status: str
