"""Tests for tenant endpoints (create validation; no DB for success path)."""

from httpx import AsyncClient


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
