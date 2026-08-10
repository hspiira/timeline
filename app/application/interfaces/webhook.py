"""Webhook dispatcher interface (event push to subscribers)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.entities.event import EventEntity


class IWebhookDispatcher(Protocol):
    """Dispatch created events to registered webhook subscriptions (push)."""

    async def dispatch(
        self, tenant_id: str, event: "EventEntity", subject_type: str
    ) -> None:
        """Notify matching subscriptions for this tenant/event. Fire-and-forget; logs errors."""
        ...
