"""Pytest configuration and fixtures for timeline.

Uses app.main:app for HTTP tests and app.infrastructure.persistence.database
for DB-dependent fixtures. All imports use app.*.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client against the FastAPI app (ASGI)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
