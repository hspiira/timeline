"""In-memory event stream broadcaster for SSE (Phase 5)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.application.interfaces.event_stream import IEventStreamBroadcaster

QUEUE_MAXSIZE = 1000

logger = logging.getLogger(__name__)


class InMemoryEventStreamBroadcaster(IEventStreamBroadcaster):
    """In-memory broadcaster: subscribers get queues; publish pushes to matching queues.

    Uses asyncio.Lock to protect _subs. publish() runs on the event loop and puts
    directly into subscriber queues; full queues are skipped (drop event).
    """

    def __init__(self) -> None:
        self._subs: dict[
            tuple[str, str | None],
            list[asyncio.Queue[dict[str, Any]]],
        ] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        tenant_id: str,
        subject_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Subscribe to new events; yields payloads until the generator is closed."""
        key = (tenant_id, subject_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        async with self._lock:
            if key not in self._subs:
                self._subs[key] = []
            self._subs[key].append(queue)
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            async with self._lock:
                if key in self._subs:
                    self._subs[key] = [q for q in self._subs[key] if q is not queue]
                    if not self._subs[key]:
                        del self._subs[key]

    async def publish(
        self,
        tenant_id: str,
        payload: dict,
        subject_id: str,
    ) -> None:
        """Push payload to all subscribers for this tenant (all-subject and this subject)."""
        async with self._lock:
            targets: list[asyncio.Queue[dict[str, Any]]] = []
            for key in [(tenant_id, None), (tenant_id, subject_id)]:
                targets.extend(self._subs.get(key, []))
        for queue in targets:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.debug(
                    "Dropping SSE event for tenant_id=%s subject_id=%s: subscriber queue full (queue=%r)",
                    tenant_id,
                    subject_id,
                    queue,
                )
