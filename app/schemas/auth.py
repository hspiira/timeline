"""Auth API schemas."""

from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    """Request body for login. Users identify tenant by code (e.g. org slug), not internal tenant_id."""

    tenant_code: str = Field(
        ...,
        min_length=1,
        description="Tenant code (e.g. org slug) to identify the tenant",
    )
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class RegisterRequest(BaseModel):
    """Request body for public registration (tenant by code)."""

    tenant_code: str = Field(..., min_length=1, description="Tenant code (e.g. org slug)")
    username: str = Field(..., min_length=1)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class SetInitialPasswordRequest(BaseModel):
    """Request body for POST /auth/set-initial-password (C2 tenant creation flow)."""

    token: str = Field(..., min_length=1, description="One-time token from set-password link")
    password: str = Field(..., min_length=8, description="New password (min 8 characters)")
    password_confirm: str = Field(..., min_length=8, description="Confirm new password")

    @model_validator(mode="after")
    def passwords_match(self) -> "SetInitialPasswordRequest":
        if self.password != self.password_confirm:
            raise ValueError("password and password_confirm must match")
        return self


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
