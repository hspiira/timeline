"""Webhook dispatcher: POST events to subscribed URLs with HMAC signing and retries."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable

import httpx

from app.application.dtos.webhook_subscription import WebhookSubscriptionForDispatch
from app.application.validators.webhook_url import validate_webhook_target_url

if TYPE_CHECKING:
    from app.domain.entities.event import EventEntity

logger = logging.getLogger(__name__)

TIMEOUT = 10.0
RETRY_DELAYS = (1, 4, 16)


def _event_payload(event: "EventEntity") -> dict[str, Any]:
    """Build JSON-serializable payload from event entity."""
    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "subject_id": event.subject_id,
        "event_type": event.event_type.value,
        "event_time": event.event_time.isoformat(),
        "payload": event.payload,
        "workflow_instance_id": event.workflow_instance_id,
        "correlation_id": event.correlation_id,
        "external_id": event.external_id,
        "source": event.source,
    }


def _sign(secret: str, body: bytes) -> str:
    """Return HMAC-SHA256 hex digest of body using secret."""
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def _matches(
    sub: WebhookSubscriptionForDispatch,
    event_type: str,
    subject_type: str,
) -> bool:
    """Return True if subscription matches event (empty filters = all)."""
    if sub.event_types and event_type not in sub.event_types:
        return False
    if sub.subject_types and subject_type not in sub.subject_types:
        return False
    return True


class WebhookDispatcher:
    """Dispatch created events to active webhook subscriptions (fire-and-forget)."""

    def __init__(
        self,
        get_subscriptions: Callable[
            [str], Awaitable[list[WebhookSubscriptionForDispatch]]
        ],
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """get_subscriptions(tenant_id) -> list[WebhookSubscriptionForDispatch] (async)."""
        self._get_subscriptions = get_subscriptions
        self._http = http_client

    async def dispatch(
        self,
        tenant_id: str,
        event: "EventEntity",
        subject_type: str,
    ) -> None:
        """Notify matching subscriptions; log errors, do not raise."""
        subs = await self._get_subscriptions(tenant_id)
        event_type = event.event_type.value
        matching = [s for s in subs if _matches(s, event_type, subject_type)]
        if not matching:
            return
        payload = _event_payload(event)
        body = json.dumps(payload).encode("utf-8")
        client = self._http or httpx.AsyncClient(timeout=TIMEOUT)
        try:
            for sub in matching:
                await self._deliver(client, sub, body)
        finally:
            if self._http is None and client is not None:
                await client.aclose()

    async def send_test(self, sub: WebhookSubscriptionForDispatch) -> bool:
        """POST a test payload to the subscription URL; return True if 2xx."""
        payload = {
            "test": True,
            "subscription_id": sub.id,
            "tenant_id": sub.tenant_id,
            "message": "Timeline webhook test delivery",
        }
        body = json.dumps(payload).encode("utf-8")
        client = self._http or httpx.AsyncClient(timeout=TIMEOUT)
        try:
            return await self._deliver(client, sub, body)
        finally:
            if self._http is None and client is not None:
                await client.aclose()

    async def _deliver(
        self,
        client: httpx.AsyncClient,
        sub: WebhookSubscriptionForDispatch,
        body: bytes,
    ) -> bool:
        """POST to target_url with signature; retry with backoff. Returns True if 2xx."""
        try:
            validate_webhook_target_url(sub.target_url)
        except ValueError as e:
            logger.warning(
                "Webhook delivery skipped (unsafe target_url): %s - %s",
                sub.target_url,
                e,
            )
            return False
        signature = _sign(sub.secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-Timeline-Signature": f"sha256={signature}",
        }
        last_error: Exception | None = None
        for i, delay in enumerate(RETRY_DELAYS):
            try:
                r = await client.post(sub.target_url, content=body, headers=headers)
                r.raise_for_status()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                logger.warning(
                    "Webhook delivery to %s failed (retry in %ss): %s",
                    sub.target_url,
                    delay,
                    e,
                )
                if i < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)
            else:
                return True
        logger.error(
            "Webhook delivery to %s failed after retries: %s",
            sub.target_url,
            last_error,
            exc_info=last_error,
        )
        return False
