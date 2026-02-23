"""Security hardening tests: cross-tenant 403, invalid tenant ID 400, 500 no traceback, CORS/config."""

import os
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.requires_db
async def test_protected_endpoint_rejects_when_tenant_header_mismatches_jwt(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """Request with valid JWT for tenant A and X-Tenant-ID for tenant B returns 403."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    # Create a second tenant so we have a valid tenant B ID.
    from tests.conftest import _TEST_CREATE_TENANT_SECRET

    secret = os.environ.get("CREATE_TENANT_SECRET", _TEST_CREATE_TENANT_SECRET)
    create_b = await client.post(
        "/api/v1/tenants",
        json={"code": "tenant-b-sec-test", "name": "Tenant B"},
        headers={"X-Create-Tenant-Secret": secret},
    )
    if create_b.status_code != 201:
        pytest.skip(f"Could not create second tenant: {create_b.status_code}")
    tenant_b_id = create_b.json()["tenant_id"]
    tenant_a_id = auth_headers["X-Tenant-ID"]
    if tenant_b_id == tenant_a_id:
        pytest.skip("Tenant IDs coincided")
    headers = {
        "Authorization": auth_headers["Authorization"],
        "X-Tenant-ID": tenant_b_id,
    }
    response = await client.get("/api/v1/subjects", headers=headers)
    assert response.status_code == 403
    assert "forbidden" in response.json().get("message", "").lower()


async def test_invalid_tenant_id_format_returns_400(client: AsyncClient) -> None:
    """Request with invalid X-Tenant-ID format (e.g. too long or bad chars) returns 400."""
    # No auth needed for this to fail at get_tenant_id.
    response = await client.get(
        "/api/v1/subjects",
        headers={"X-Tenant-ID": "x" * 65},
    )
    assert response.status_code == 400
    assert "invalid" in response.json().get("message", "").lower() or "format" in response.json().get("message", "").lower()


async def test_invalid_tenant_id_format_special_chars_returns_400(client: AsyncClient) -> None:
    """X-Tenant-ID with disallowed characters returns 400."""
    response = await client.get(
        "/api/v1/subjects",
        headers={"X-Tenant-ID": "tenant/../../etc"},
    )
    assert response.status_code == 400


async def test_500_response_does_not_include_traceback_when_debug_false() -> None:
    """With debug=False, generic exception handler returns a safe message (no traceback)."""
    import json

    from app.core.exception_handlers import _generic_exception_handler

    class FakeRequest:
        pass

    with patch("app.core.exception_handlers.get_settings") as m_get_settings:
        m_get_settings.return_value.debug = False
        response = _generic_exception_handler(FakeRequest(), ValueError("sensitive"))
    body = json.loads(response.body.decode())
    msg = body.get("message", "")
    assert "Traceback" not in msg
    assert "File " not in msg
    assert "internal" in msg.lower() or "error" in msg.lower()


async def test_settings_reject_allowed_origins_wildcard() -> None:
    """Settings validation rejects ALLOWED_ORIGINS=* (insecure with credentials)."""
    with patch.dict(os.environ, {"ALLOWED_ORIGINS": "*"}, clear=False):
        get_settings.cache_clear()
        try:
            with pytest.raises(ValueError, match="allowed_origins"):
                get_settings()
        finally:
            get_settings.cache_clear()


async def test_auth_rate_per_tenant_code_enforced() -> None:
    """After AUTH_PER_TENANT_CODE_LIMIT attempts for same tenant_code, 429 is raised."""
    from app.core.limiter import (
        AUTH_PER_TENANT_CODE_LIMIT,
        check_auth_rate_per_tenant_code,
    )

    tenant = "rate-limit-tenant"
    for _ in range(AUTH_PER_TENANT_CODE_LIMIT):
        check_auth_rate_per_tenant_code(tenant)
    with pytest.raises(Exception) as exc_info:
        check_auth_rate_per_tenant_code(tenant)
    assert exc_info.value.status_code == 429


async def test_settings_reject_debug_true_in_production() -> None:
    """Settings validation rejects debug=True when telemetry_environment is production."""
    with patch.dict(
        os.environ,
        {"TELEMETRY_ENVIRONMENT": "production", "DEBUG": "true"},
        clear=False,
    ):
        get_settings.cache_clear()
        try:
            with pytest.raises(ValueError, match="debug"):
                get_settings()
        finally:
            get_settings.cache_clear()


@pytest.mark.requires_db
async def test_audit_log_captures_tenant_id_and_resource_for_mutation(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """After a successful mutation, audit log contains tenant_id and resource_type (and resource_id when in path)."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    # Perform a mutation that is logged by AuditLogMiddleware (POST to a resource under /api/v1/)
    create_resp = await client.post(
        "/api/v1/subjects",
        headers=auth_headers,
        json={"subject_type": "audit_test", "display_name": "Audit test subject"},
    )
    if create_resp.status_code not in (200, 201):
        pytest.skip(f"Create subject failed: {create_resp.status_code} {create_resp.text}")
    # List audit log (admin has audit:read from tenant init)
    list_resp = await client.get(
        "/api/v1/audit-log",
        headers=auth_headers,
        params={"limit": 10},
    )
    if list_resp.status_code != 200:
        pytest.skip(f"List audit log failed: {list_resp.status_code} (missing audit:read?)")
    data = list_resp.json()
    items = data.get("items") or []
    assert len(items) >= 1, "Expected at least one audit log entry after mutation"
    entry = items[0]
    assert entry.get("tenant_id"), "Audit entry must have tenant_id"
    assert entry.get("resource_type"), "Audit entry must have resource_type"
    subjects_entries = [e for e in items if e.get("resource_type") == "subjects"]
    assert len(subjects_entries) >= 1, "Expected an entry for resource_type subjects"
