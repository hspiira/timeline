"""Security tests for email account webhook (signature and secret required)."""

import os

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.requires_db
async def test_webhook_when_secret_not_configured_returns_503(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """POST /email-accounts/{id}/webhook returns 503 when EMAIL_WEBHOOK_SECRET is not set."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    prev = os.environ.pop("EMAIL_WEBHOOK_SECRET", None)
    get_settings.cache_clear()
    try:
        response = await client.post(
            "/api/v1/email-accounts/some-account-id/webhook",
            json={"test": "body"},
            headers=auth_headers,
        )
        assert response.status_code == 503
        assert "not configured" in response.json().get("message", "").lower()
    finally:
        if prev is not None:
            os.environ["EMAIL_WEBHOOK_SECRET"] = prev
        get_settings.cache_clear()


@pytest.mark.requires_db
async def test_webhook_with_wrong_signature_returns_401(
    client: AsyncClient,
    auth_headers: dict[str, str] | None,
) -> None:
    """POST /email-accounts/{id}/webhook with invalid X-Webhook-Signature-256 returns 401."""
    if auth_headers is None:
        pytest.skip("auth_headers not available (Postgres not configured)")
    prev = os.environ.get("EMAIL_WEBHOOK_SECRET")
    os.environ["EMAIL_WEBHOOK_SECRET"] = "test-webhook-secret"
    get_settings.cache_clear()
    try:
        response = await client.post(
            "/api/v1/email-accounts/some-account-id/webhook",
            json={"test": "body"},
            headers={**auth_headers, "X-Webhook-Signature-256": "sha256=wrong"},
        )
        assert response.status_code == 401
        assert "signature" in response.json().get("message", "").lower()
    finally:
        if prev is not None:
            os.environ["EMAIL_WEBHOOK_SECRET"] = prev
        else:
            os.environ.pop("EMAIL_WEBHOOK_SECRET", None)
        get_settings.cache_clear()
