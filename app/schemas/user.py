"""User API schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Request body for creating a user (tenant-scoped)."""

    username: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Request body for updating current user (partial)."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)


class UserResponse(BaseModel):
    """User response (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    username: str
    email: str
    is_active: bool
