"""Auth API schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for login. Users identify tenant by code (e.g. org slug), not internal tenant_id."""

    tenant_code: str = Field(
        ...,
        min_length=1,
        description="Tenant code (e.g. org slug) to identify the tenant",
    )
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
