"""Tests for tenant endpoints (create validation; no DB for success path)."""

import os
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import _TEST_CREATE_TENANT_SECRET


async def test_create_tenant_missing_body_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/tenants with no body returns 422."""
    response = await client.post("/api/v1/tenants", json={})
    assert response.status_code == 422


async def test_create_tenant_empty_code_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/tenants with empty code fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={"code": "", "name": "Acme Corp"},
    )
    assert response.status_code == 422


async def test_create_tenant_code_too_short_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/tenants with code shorter than 3 chars fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={"code": "ab", "name": "Acme Corp"},
    )
    assert response.status_code == 422


async def test_create_tenant_invalid_code_pattern_returns_422(
    client: AsyncClient,
) -> None:
    """POST /api/v1/tenants with code that has invalid chars (e.g. underscore) fails.

    Code is normalized (lowercase, spaces to hyphens) before pattern check;
    underscore is not allowed and stays after normalization.
    """
    response = await client.post(
        "/api/v1/tenants",
        json={"code": "acme_corp", "name": "Acme Corp"},
    )
    assert response.status_code == 422


async def test_create_tenant_empty_name_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/tenants with empty name fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={"code": "acme", "name": ""},
    )
    assert response.status_code == 422


async def test_create_tenant_name_too_long_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/tenants with name longer than 255 chars fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={"code": "acme", "name": "x" * 256},
    )
    assert response.status_code == 422


async def test_create_tenant_admin_initial_password_too_short_returns_422(
    client: AsyncClient,
) -> None:
    """POST /api/v1/tenants with admin_initial_password shorter than 8 chars fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={"code": "acme", "name": "Acme", "admin_initial_password": "short"},
    )
    assert response.status_code == 422


async def test_create_tenant_when_secret_not_configured_returns_503(
    client: AsyncClient,
) -> None:
    """POST /api/v1/tenants returns 503 when CREATE_TENANT_SECRET is not set."""
    env_prev = os.environ.pop("CREATE_TENANT_SECRET", None)
    get_settings.cache_clear()
    try:
        response = await client.post(
            "/api/v1/tenants",
            json={"code": "acme", "name": "Acme Corp"},
        )
        assert response.status_code == 503
        assert "not configured" in response.json().get("message", "").lower()
    finally:
        if env_prev is not None:
            os.environ["CREATE_TENANT_SECRET"] = env_prev
        get_settings.cache_clear()


async def test_create_tenant_without_secret_returns_401(client: AsyncClient) -> None:
    """POST /api/v1/tenants without X-Create-Tenant-Secret returns 401 when secret is configured."""
    with patch.dict(os.environ, {"CREATE_TENANT_SECRET": "required-secret"}, clear=False):
        get_settings.cache_clear()
        try:
            response = await client.post(
                "/api/v1/tenants",
                json={"code": "acme", "name": "Acme Corp"},
            )
            assert response.status_code == 401
            assert "unauthorized" in response.json().get("message", "").lower()
        finally:
            get_settings.cache_clear()


async def test_create_tenant_with_wrong_secret_returns_401(client: AsyncClient) -> None:
    """POST /api/v1/tenants with wrong X-Create-Tenant-Secret returns 401."""
    with patch.dict(os.environ, {"CREATE_TENANT_SECRET": "correct-secret"}, clear=False):
        get_settings.cache_clear()
        try:
            response = await client.post(
                "/api/v1/tenants",
                json={"code": "acme", "name": "Acme Corp"},
                headers={"X-Create-Tenant-Secret": "wrong-secret"},
            )
            assert response.status_code == 401
        finally:
            get_settings.cache_clear()


@pytest.mark.requires_db
async def test_create_tenant_with_correct_secret_returns_201(client: AsyncClient) -> None:
    """POST /api/v1/tenants with correct X-Create-Tenant-Secret returns 201 (requires Postgres)."""
    from app.infrastructure.persistence.database import AsyncSessionLocal, _ensure_engine

    _ensure_engine()
    if AsyncSessionLocal is None:
        pytest.skip("Postgres not configured")
    if "CREATE_TENANT_SECRET" not in os.environ:
        os.environ["CREATE_TENANT_SECRET"] = _TEST_CREATE_TENANT_SECRET
        get_settings.cache_clear()
    secret = os.environ.get("CREATE_TENANT_SECRET", _TEST_CREATE_TENANT_SECRET)
    code = f"acme-{__import__('uuid').uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/tenants",
        json={
            "code": code,
            "name": "Acme Corp",
            "admin_initial_password": "AcmeAdminPass123!",
        },
        headers={"X-Create-Tenant-Secret": secret},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tenant_code"] == code
    assert "tenant_id" in data
    assert "admin_username" in data
    assert "admin_email" in data
    assert "admin_password" not in data
    # C2: set_password_url and set_password_expires_at when SET_PASSWORD_BASE_URL is set
    assert "set_password_url" in data
    assert "set_password_expires_at" in data
