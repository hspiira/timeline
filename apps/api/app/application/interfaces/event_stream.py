"""Event stream broadcaster interface for SSE (Server-Sent Events) push (Phase 5)."""

from collections.abc import AsyncIterator
from typing import Protocol


class IEventStreamBroadcaster(Protocol):
    """Protocol for broadcasting new events to SSE (and other) subscribers."""

    def subscribe(
        self,
        tenant_id: str,
        subject_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Return an async iterator of event payloads for the tenant, optionally
        filtered to one subject. Implementations are async generators, so this is not
        ``async def``."""
        ...

    async def publish(
        self,
        tenant_id: str,
        payload: dict,
        subject_id: str,
    ) -> None:
        """Notify all subscribers for this tenant (and those subscribed to this subject_id). payload must be JSON-serializable."""
        ...
