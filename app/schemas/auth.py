"""Auth API schemas."""

from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    """Request body for login: email and password, organisation only when ambiguous.

    Nobody types an organisation code. The email identifies the person, and the
    organisation is worked out from it. ``tenant_id`` is needed only when that email
    belongs to more than one organisation, in which case the client first calls
    ``POST /auth/organisations`` and shows a picker.
    """

    email: EmailStr = Field(..., description="The person's email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    tenant_id: str | None = Field(
        default=None,
        description=(
            "Organisation to sign in to. Omit when the email belongs to exactly one; "
            "required when it belongs to several."
        ),
    )


class OrganisationsRequest(BaseModel):
    """Request body for POST /auth/organisations: which organisations does this email have?"""

    email: EmailStr = Field(..., description="The person's email address")


class OrganisationSummary(BaseModel):
    """One organisation a person can sign in to. Name is for display; id is what login takes."""

    tenant_id: str
    name: str


class OrganisationsResponse(BaseModel):
    """Organisations available for an email.

    Always returns 200 with a possibly empty list, so an unregistered email is not
    distinguishable from one with no active memberships.
    """

    organisations: list[OrganisationSummary] = []


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
    """JWT access token response.

    The refresh token is deliberately **not** here. It is set as an httpOnly cookie
    so page scripts cannot read it, which is what the web client expects (see
    ui.timeline ``src/lib/api-client.ts``). The client renews quietly against
    ``POST /auth/refresh`` so a working day is never interrupted.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = Field(
        default=None, description="Access token lifetime in seconds"
    )
