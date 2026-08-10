"""Tests for auth endpoints (validation and error responses; no DB for success path)."""

import os
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import _TEST_CREATE_TENANT_SECRET


async def test_login_missing_body_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with no body returns 422."""
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422


async def test_login_invalid_email_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with something that is not an email fails validation."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


async def test_login_short_password_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with password shorter than 8 chars fails validation."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 422


async def test_login_no_longer_accepts_an_organisation_code(
    client: AsyncClient,
) -> None:
    """An organisation code alone is not enough to sign in; email is required.

    Guards against the old three-field form quietly coming back.
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={"tenant_code": "acme", "username": "user", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.requires_db
async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with an unregistered email returns a generic 401.

    Sign-in takes an email and no organisation code. An unknown email must fail with
    exactly the same message as a wrong password, so neither can be used to work out
    whether an address is registered.
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    assert response.json().get("message") == "Invalid credentials"


@pytest.mark.requires_db
async def test_organisations_for_unknown_email_returns_empty_200(
    client: AsyncClient,
) -> None:
    """POST /api/v1/auth/organisations always returns 200, empty for an unknown email.

    A 404 here would let anyone probe which addresses exist.
    """
    response = await client.post(
        "/api/v1/auth/organisations",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {"organisations": []}


async def test_register_missing_body_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/register with no body returns 422."""
    response = await client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422


async def test_register_invalid_email_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/register with invalid email fails validation."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_code": "acme",
            "username": "user",
            "email": "not-an-email",
            "password": "password123",
        },
    )
    assert response.status_code == 422


async def test_public_registration_is_disabled(client: AsyncClient) -> None:
    """POST /api/v1/auth/register is disabled and says so.

    It used to let anyone who knew an organisation's code create an account inside
    that organisation, and codes are not secret. Adding people is now an
    authenticated action on POST /api/v1/users.
    """
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_code": "any-code",
            "username": "user",
            "email": "user@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 403
    assert "POST /api/v1/users" in response.json().get("message", "")



@pytest.mark.requires_db
async def test_set_initial_password_invalid_token_returns_400(client: AsyncClient) -> None:
    """POST /api/v1/auth/set-initial-password with invalid/expired token returns 400.

    Requires Postgres (token store).
    """
    from app.infrastructure.persistence.database import AsyncSessionLocal, _ensure_engine

    _ensure_engine()
    if AsyncSessionLocal is None:
        pytest.skip("Postgres not configured")
    response = await client.post(
        "/api/v1/auth/set-initial-password",
        json={
            "token": "invalid-or-expired-token",
            "password": "NewPassword123!",
            "password_confirm": "NewPassword123!",
        },
    )
    # 400 when token invalid; 503 when DB not configured (e.g. DATABASE_URL unset)
    assert response.status_code in (400, 503)
    if response.status_code == 400:
        assert "Invalid or expired link" in response.json().get("detail", "")
