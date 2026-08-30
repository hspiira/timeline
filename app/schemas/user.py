"""User API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Request body for creating a user (tenant-scoped)."""

    username: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    password: str | None = Field(
        default=None,
        min_length=8,
        description=(
            "Optional. Omit to invite the person instead: a one-time link is returned "
            "and they choose their own password. Prefer omitting it — an administrator "
            "who sets someone's password knows their credential, which undermines the "
            "attribution recorded on their events."
        ),
    )


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
    permissions: list[str] = []


class UserCreateResponse(UserResponse):
    """Response after adding someone to an organisation.

    When the caller omitted ``password``, ``invite_token`` carries a one-time link
    the person uses to set their own. It is always present in that case, so an
    invited member is never left with no way in even when SET_PASSWORD_BASE_URL is
    unconfigured; ``invite_url`` is the ready-made link and is filled only when it is.
    """

    invite_token: str | None = None
    invite_url: str | None = None
    invite_expires_at: datetime | None = None
