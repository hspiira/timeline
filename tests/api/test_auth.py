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


async def test_login_empty_tenant_code_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with empty tenant_code fails validation."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_code": "",
            "username": "user",
            "password": "password123",
        },
    )
    assert response.status_code == 422


async def test_login_short_password_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with password shorter than 8 chars fails validation."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_code": "acme",
            "username": "user",
            "password": "short",
        },
    )
    assert response.status_code == 422


async def test_login_invalid_credentials_returns_401(client: AsyncClient) -> None:
    """POST /api/v1/auth/login with valid shape but unknown tenant returns 401.

    Does not require a real DB; app resolves tenant by code and returns 401
    when tenant is not found or credentials fail. Message must be generic
    (same as wrong password) to avoid tenant enumeration.
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_code": "nonexistent-tenant-code-xyz",
            "username": "nobody",
            "password": "password123",
        },
    )
    assert response.status_code == 401
    assert response.json().get("message") == "Invalid credentials"


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


async def test_register_invalid_tenant_code_returns_400_generic(
    client: AsyncClient,
) -> None:
    """POST /api/v1/auth/register with unknown tenant_code returns 400 with generic message (no enumeration)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_code": "nonexistent-tenant-code-xyz",
            "username": "user",
            "email": "user@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert response.json().get("message") == "Registration failed"


@pytest.mark.requires_db
async def test_register_duplicate_user_returns_400_generic(client: AsyncClient) -> None:
    """POST /api/v1/auth/register with existing email returns 400 with generic message (no enumeration)."""
    from app.infrastructure.persistence.database import AsyncSessionLocal, _ensure_engine

    _ensure_engine()
    if AsyncSessionLocal is None:
        pytest.skip("Postgres not configured")

    if "CREATE_TENANT_SECRET" not in os.environ:
        os.environ["CREATE_TENANT_SECRET"] = _TEST_CREATE_TENANT_SECRET
        get_settings.cache_clear()
    secret = os.environ.get("CREATE_TENANT_SECRET", _TEST_CREATE_TENANT_SECRET)
    code = f"reg-{uuid.uuid4().hex[:10]}"
    create_resp = await client.post(
        "/api/v1/tenants",
        json={"code": code, "name": "Reg Test"},
        headers={"X-Create-Tenant-Secret": secret},
    )
    if create_resp.status_code != 201:
        pytest.skip(f"Could not create tenant: {create_resp.status_code}")

    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    reg1 = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_code": code,
            "username": "user1",
            "email": email,
            "password": "password123",
        },
    )
    assert reg1.status_code == 201

    reg2 = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_code": code,
            "username": "user2",
            "email": email,
            "password": "otherpass456",
        },
    )
    assert reg2.status_code == 400
    assert reg2.json().get("message") == "Registration failed"


async def test_set_initial_password_passwords_mismatch_returns_422(
    client: AsyncClient,
) -> None:
    """POST /api/v1/auth/set-initial-password with password != password_confirm returns 422."""
    response = await client.post(
        "/api/v1/auth/set-initial-password",
        json={
            "token": "any-token",
            "password": "NewPassword123!",
            "password_confirm": "OtherPassword123!",
        },
    )
    assert response.status_code == 422


@pytest.mark.requires_db
async def test_set_initial_password_invalid_token_returns_400(client: AsyncClient) -> None:
    """POST /api/v1/auth/set-initial-password with invalid/expired token returns 400.

    Requires Postgres (token store); when Firestore, dependency raises and returns 503.
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
    # 400 when token invalid; 503 when backend is not Postgres (table doesn't exist or Firestore)
    assert response.status_code in (400, 503)
    if response.status_code == 400:
        assert "Invalid or expired link" in response.json().get("detail", "")
