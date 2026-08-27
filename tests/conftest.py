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
# Import the module, not the names: _ensure_engine() rebinds AsyncSessionLocal as a
# module global, and a from-import would capture the pre-init None forever.
from app.infrastructure.persistence import database as _database
from app.infrastructure.persistence.database import _ensure_engine
from app.main import app

# When CREATE_TENANT_SECRET is not set, tests that create tenants set this so
# POST /api/v1/tenants succeeds. The app reads settings on each request.
_TEST_CREATE_TENANT_SECRET = "test-create-tenant-secret"


@pytest.fixture(autouse=True)
def _isolate_rate_limits():
    """Clear the rate limit windows between tests.

    Limits are keyed on client IP and every test shares one, so without this the
    sixth test to create a tenant spends the fifth one's budget and gets a 429.
    Reset rather than disable, so the limits stay exercised.
    """
    from app.core import limiter as limiter_mod

    limiter_mod.limiter.reset()
    limiter_mod._auth_per_tenant.clear()
    yield


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client against the FastAPI app (ASGI)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def _reset_db_engine():
    """Dispose the shared async engine after every test.

    The engine and its connection pool are module-level globals, but pytest-asyncio
    gives each test its own event loop. A pooled connection created under one loop
    and reused under the next raises "Event loop is closed", which shows up as a
    failure in whichever test happens to run second. Disposing and clearing the
    globals makes _ensure_engine() rebuild against the current loop.
    """
    yield
    if _database.engine is not None:
        await _database.engine.dispose()
        _database.engine = None
        _database.AsyncSessionLocal = None


@pytest.fixture
async def db_session() -> AsyncSession:
    """Database session for repository/integration tests. Rolls back after test.

    Requires DATABASE_URL. Skips (pytest.skip) when Postgres is not configured.
    Use @pytest.mark.requires_db to mark tests that need this fixture;
    run without DB via: pytest -m 'not requires_db'.
    """
    _ensure_engine()
    if _database.AsyncSessionLocal is None:
        pytest.skip(
            "Postgres not configured: set DATABASE_URL and run: uv run alembic upgrade head"
        )
    async with _database.AsyncSessionLocal() as session:
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
    if _database.AsyncSessionLocal is None:
        pytest.skip(
            "Postgres not configured: set DATABASE_URL and run: uv run alembic upgrade head"
        )
    # Ensure tenant creation is allowed in tests (secret required by endpoint).
    if "CREATE_TENANT_SECRET" not in os.environ:
        os.environ["CREATE_TENANT_SECRET"] = _TEST_CREATE_TENANT_SECRET
        get_settings.cache_clear()
    secret = os.environ.get("CREATE_TENANT_SECRET", _TEST_CREATE_TENANT_SECRET)

    # 15 characters exactly: the tenant code column caps at 15 (app/schemas/tenant.py).
    # A longer code made every test using this fixture skip on a 422 instead of running.
    code = f"test-{uuid.uuid4().hex[:10]}"
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
    # Fail rather than skip: a fixture that cannot build its tenant is broken, and
    # skipping here hid eleven security tests that had never run.
    assert create_resp.status_code == 201, (
        f"Could not create test tenant: {create_resp.status_code} {create_resp.text}"
    )
    data = create_resp.json()
    tenant_id = data["tenant_id"]
    assert "admin_password" not in data
    # Sign in by email, which is what LoginRequest takes since the email-signin work.
    # tenant_id is sent explicitly rather than relying on the email resolving to one
    # organisation, so the fixture keeps working once a test creates a second tenant
    # for the same address.
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": data["admin_email"],
            "password": admin_password,
            "tenant_id": tenant_id,
        },
    )
    assert login_resp.status_code == 200, (
        f"Could not login as admin: {login_resp.status_code} {login_resp.text}"
    )
    token = login_resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }
