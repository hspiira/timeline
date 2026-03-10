"""Event stream broadcaster interface for SSE (Server-Sent Events) push (Phase 5)."""

from collections.abc import AsyncIterator
from typing import Protocol


class IEventStreamBroadcaster(Protocol):
    """Protocol for broadcasting new events to SSE (and other) subscribers."""

    async def subscribe(
        self,
        tenant_id: str,
        subject_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Subscribe to new events for tenant (and optionally one subject). Yields JSON-serializable event payloads."""
        ...

    def publish(
        self,
        tenant_id: str,
        payload: dict,
        subject_id: str,
    ) -> None:
        """Notify all subscribers for this tenant (and those subscribed to this subject_id). payload must be JSON-serializable."""
        ...
