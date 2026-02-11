"""Smoke tests for health and app wiring."""

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    """GET /api/v1/health returns 200 and status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


async def test_root_returns_html(client: AsyncClient) -> None:
    """GET / returns HTML landing page."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
