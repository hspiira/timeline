"""Tests for auth endpoints (validation and error responses; no DB for success path)."""

from httpx import AsyncClient


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
    when tenant is not found or credentials fail.
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
