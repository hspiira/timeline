"""Tests for user endpoint schemas (invite path; no DB)."""

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreateRequest, UserCreateResponse


def test_user_create_request_allows_omitting_password() -> None:
    """Omitting password is the invite path and must validate.

    An administrator who sets someone else's password knows their credential, which
    undermines the attribution recorded on that person's events. Inviting is the
    default, so the schema has to permit it.
    """
    body = UserCreateRequest(username="asha", email="asha@acme.example")
    assert body.password is None


def test_user_create_request_still_enforces_password_length() -> None:
    """A supplied password is still held to the minimum length."""
    with pytest.raises(ValidationError):
        UserCreateRequest(username="asha", email="asha@acme.example", password="short")


def test_user_create_response_carries_invite_fields() -> None:
    """The response model can return a one-time invite link."""
    response = UserCreateResponse(
        id="u1",
        tenant_id="t1",
        username="asha",
        email="asha@acme.example",
        is_active=True,
        invite_token="raw-token",
    )
    assert response.invite_token == "raw-token"
    assert response.invite_url is None
