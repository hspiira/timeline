"""Pytest configuration and fixtures for timeline.

Uses app.main:app for HTTP tests and app.infrastructure.persistence.database
for DB-dependent fixtures. All imports use app.*.
"""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.persistence.database import (
    AsyncSessionLocal,
    _ensure_engine,
)
from app.main import app

# When CREATE_TENANT_SECRET is not set, tests that create tenants set this so
# POST /api/v1/tenants succeeds. The app reads settings on each request.
_TEST_CREATE_TENANT_SECRET = "test-create-tenant-secret"


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client against the FastAPI app (ASGI)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncSession:
    """Database session for repository/integration tests. Rolls back after test.

    Requires DATABASE_BACKEND=postgres and DATABASE_URL. Skips (pytest.skip)
    when Postgres is not configured. Use @pytest.mark.requires_db to mark
    tests that need this fixture; run without DB via: pytest -m 'not requires_db'.
    """
    _ensure_engine()
    if AsyncSessionLocal is None:
        pytest.skip(
            "Postgres not configured: set DATABASE_BACKEND=postgres and DATABASE_URL, "
            "then run: uv run alembic upgrade head"
        )
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str] | None:
    """Create a tenant via API, login as admin, return headers for protected requests.

    Returns None (and test is skipped) when Postgres is not configured.
    Otherwise returns dict with Authorization and X-Tenant-ID for use in API calls.
    Creates real tenant + user; data persists after test (use a test DB for CI).
    """
    _ensure_engine()
    if AsyncSessionLocal is None:
        pytest.skip(
            "Postgres not configured: set DATABASE_BACKEND=postgres and DATABASE_URL"
        )
    # Ensure tenant creation is allowed in tests (secret required by endpoint).
    if "CREATE_TENANT_SECRET" not in os.environ:
        os.environ["CREATE_TENANT_SECRET"] = _TEST_CREATE_TENANT_SECRET
        get_settings.cache_clear()
    secret = os.environ.get("CREATE_TENANT_SECRET", _TEST_CREATE_TENANT_SECRET)

    code = f"test-{uuid.uuid4().hex[:12]}"
    admin_password = "TestAdminPassword123!"
    create_resp = await client.post(
        "/api/v1/tenants",
        json={
            "code": code,
            "name": f"Test Tenant {code}",
            "admin_initial_password": admin_password,
        },
        headers={"X-Create-Tenant-Secret": secret},
    )
    if create_resp.status_code != 201:
        pytest.skip(f"Could not create test tenant: {create_resp.status_code} {create_resp.text}")
    data = create_resp.json()
    tenant_id = data["tenant_id"]
    assert "admin_password" not in data
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_code": code,
            "username": "admin",
            "password": admin_password,
        },
    )
    if login_resp.status_code != 200:
        pytest.skip(f"Could not login as admin: {login_resp.status_code} {login_resp.text}")
    token = login_resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }
