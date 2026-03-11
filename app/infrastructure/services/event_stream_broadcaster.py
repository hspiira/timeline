"""In-memory event stream broadcaster for SSE (Phase 5)."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from typing import Any

from app.application.interfaces.event_stream import IEventStreamBroadcaster

QUEUE_MAXSIZE = 1000


class InMemoryEventStreamBroadcaster(IEventStreamBroadcaster):
    """In-memory broadcaster: subscribers get queues; publish pushes to matching queues.

    Uses threading.Lock to protect _subs; publish() schedules put_nowait on each
    subscriber's event loop via call_soon_threadsafe so the queue is never mutated
    from another thread. Drops events for closed loops to avoid RuntimeError in publish path.
    """

    def __init__(self) -> None:
        self._subs: dict[
            tuple[str, str | None],
            list[tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]],
        ] = {}
        self._lock = threading.Lock()

    async def subscribe(
        self,
        tenant_id: str,
        subject_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Subscribe to new events; yields payloads until the generator is closed."""
        key = (tenant_id, subject_id)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        with self._lock:
            if key not in self._subs:
                self._subs[key] = []
            self._subs[key].append((loop, queue))
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            with self._lock:
                if key in self._subs:
                    self._subs[key] = [
                        item for item in self._subs[key] if item[1] is not queue
                    ]
                    if not self._subs[key]:
                        del self._subs[key]

    async def publish(
        self,
        tenant_id: str,
        payload: dict,
        subject_id: str,
    ) -> None:
        """Push payload to all subscribers for this tenant (all-subject and this subject)."""
        with self._lock:
            targets: list[
                tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]
            ] = []
            for key in [(tenant_id, None), (tenant_id, subject_id)]:
                targets.extend(self._subs.get(key, []))
        for loop, queue in targets:
            InMemoryEventStreamBroadcaster._put_nowait_safely(loop, queue, payload)

    @staticmethod
    def _put_nowait_safely(
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[dict[str, Any]],
        payload: dict[str, Any],
    ) -> None:
        try:
            if loop.is_closed():
                return
            loop.call_soon_threadsafe(
                lambda: InMemoryEventStreamBroadcaster._put_nowait(queue, payload)
            )
        except RuntimeError:
            pass

    @staticmethod
    def _put_nowait(
        queue: asyncio.Queue[dict[str, Any]],
        payload: dict[str, Any],
    ) -> None:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass
