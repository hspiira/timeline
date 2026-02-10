"""Tenant API schemas."""

from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    """Request body for creating a new tenant with admin user."""

    code: str = Field(..., min_length=1, max_length=64, description="Unique tenant code")
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    admin_password: str | None = Field(
        default=None,
        min_length=8,
        description="Admin user password; generated if omitted",
    )


class TenantCreateResponse(BaseModel):
    """Response after tenant creation (admin password returned only once)."""

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str
    admin_password: str
