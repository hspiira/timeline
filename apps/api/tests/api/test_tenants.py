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
    """POST /api/v1/tenants returns 503 when CREATE_TENANT_SECRET is not set.

    Sets the variable to empty rather than removing it: settings also load from a
    local .env file, so simply popping the environment variable leaves a value in
    place on any machine whose .env defines one. An explicit empty environment
    variable overrides the file, which keeps this test independent of the developer's
    setup.
    """
    env_prev = os.environ.get("CREATE_TENANT_SECRET")
    os.environ["CREATE_TENANT_SECRET"] = ""
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
        else:
            os.environ.pop("CREATE_TENANT_SECRET", None)
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
    from app.infrastructure.persistence import database as _database
    from app.infrastructure.persistence.database import _ensure_engine

    _ensure_engine()
    # Read the module attribute, not a name bound at import time: _ensure_engine sets
    # database.AsyncSessionLocal, so a direct "from ... import AsyncSessionLocal" keeps
    # the None it was bound to and skips the test unconditionally.
    if _database.AsyncSessionLocal is None:
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


async def test_create_tenant_rejects_invalid_admin_email(client: AsyncClient) -> None:
    """POST /api/v1/tenants with a malformed admin_email fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={
            "code": "acme-corp",
            "name": "Acme Corp",
            "admin_email": "not-an-email",
            "admin_initial_password": "correct horse battery",
        },
    )
    assert response.status_code == 422


async def test_create_tenant_admin_username_cannot_be_empty(client: AsyncClient) -> None:
    """POST /api/v1/tenants with an empty admin_username fails validation."""
    response = await client.post(
        "/api/v1/tenants",
        json={
            "code": "acme-corp",
            "name": "Acme Corp",
            "admin_username": "",
        },
    )
    assert response.status_code == 422


def test_tenant_create_response_can_carry_a_token() -> None:
    """The response model has somewhere to put the one-time token.

    Without this field a tenant created while SET_PASSWORD_BASE_URL is unset is
    live and unenterable: the generated password is never returned and the minted
    token has nowhere to go. Regression guard for that shape.
    """
    from app.schemas.tenant import TenantCreateResponse

    response = TenantCreateResponse(
        tenant_id="t1",
        tenant_code="acme",
        tenant_name="Acme",
        admin_username="admin",
        admin_email="admin@acme.example",
        set_password_token="raw-token",
    )
    assert response.set_password_token == "raw-token"
    assert response.set_password_url is None


def test_resolve_way_in_returns_token_without_base_url() -> None:
    """With no password supplied and no base URL, the raw token is still returned."""
    from app.api.v1.endpoints.tenants import _resolve_way_in
    from app.application.dtos.tenant import TenantCreationResult

    result = TenantCreationResult(
        tenant_id="t1",
        tenant_code="acme",
        tenant_name="Acme",
        admin_username="admin",
        admin_email="admin@acme.example",
        set_password_token="raw-token",
    )
    with patch("app.api.v1.endpoints.tenants.get_settings") as mock_settings:
        mock_settings.return_value.set_password_base_url = None
        token, url, _expires = _resolve_way_in(result, admin_password=None)
    assert token == "raw-token"
    assert url is None


def test_resolve_way_in_withholds_token_when_password_supplied() -> None:
    """A caller who set the password can already sign in, so no token is disclosed."""
    from app.api.v1.endpoints.tenants import _resolve_way_in
    from app.application.dtos.tenant import TenantCreationResult

    result = TenantCreationResult(
        tenant_id="t1",
        tenant_code="acme",
        tenant_name="Acme",
        admin_username="admin",
        admin_email="admin@acme.example",
        set_password_token="raw-token",
    )
    token, url, expires = _resolve_way_in(result, admin_password="chosen-password")
    assert (token, url, expires) == (None, None, None)


def test_resolve_way_in_refuses_to_leave_a_tenant_unenterable() -> None:
    """No password and no token must raise, not return a tenant nobody can enter."""
    from fastapi import HTTPException

    from app.api.v1.endpoints.tenants import _resolve_way_in
    from app.application.dtos.tenant import TenantCreationResult

    result = TenantCreationResult(
        tenant_id="t1",
        tenant_code="acme",
        tenant_name="Acme",
        admin_username="admin",
        admin_email="admin@acme.example",
        set_password_token=None,
    )
    with pytest.raises(HTTPException) as exc_info:
        _resolve_way_in(result, admin_password=None)
    assert exc_info.value.status_code == 503
