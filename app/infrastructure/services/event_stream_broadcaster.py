"""In-memory event stream broadcaster for SSE (Phase 5)."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator

from app.application.interfaces.event_stream import IEventStreamBroadcaster

QUEUE_MAXSIZE = 1000


class InMemoryEventStreamBroadcaster(IEventStreamBroadcaster):
    """In-memory broadcaster: subscribers get queues; publish pushes to matching queues.

    Uses threading.Lock so sync publish() can run without awaiting; subscribe() is async.
    When replacing with Redis pub/sub, make publish async and use asyncio.Lock throughout.
    """

    def __init__(self) -> None:
        self._subs: dict[tuple[str, str | None], list[asyncio.Queue]] = {}
        self._lock = threading.Lock()

    async def subscribe(
        self,
        tenant_id: str,
        subject_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Subscribe to new events; yields payloads until the generator is closed."""
        key = (tenant_id, subject_id)
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        with self._lock:
            if key not in self._subs:
                self._subs[key] = []
            self._subs[key].append(queue)
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            with self._lock:
                if key in self._subs:
                    self._subs[key] = [q for q in self._subs[key] if q is not queue]
                    if not self._subs[key]:
                        del self._subs[key]

    def publish(
        self,
        tenant_id: str,
        payload: dict,
        subject_id: str,
    ) -> None:
        """Push payload to all subscribers for this tenant (all-subject and this subject)."""
        with self._lock:
            queues: list[asyncio.Queue[dict]] = []
            for key in [(tenant_id, None), (tenant_id, subject_id)]:
                queues.extend(self._subs.get(key, []))
        for queue in queues:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass
