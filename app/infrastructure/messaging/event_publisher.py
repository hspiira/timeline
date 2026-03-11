"""Redis event publisher for SSE (Phase 5): cross-process event stream."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)


class RedisEventPublisher:
    """Publishes new events to Redis pub/sub for SSE subscribers across all workers.

    Implements IEventStreamBroadcaster. Use when redis_enabled and cache.redis
    is available; otherwise use InMemoryEventStreamBroadcaster (single-process).
    """

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def publish(
        self, tenant_id: str, payload: dict, subject_id: str
    ) -> None:
        """Fire-and-forget publish: schedule coroutine without awaiting."""
        body = json.dumps(payload)
        asyncio.create_task(
            self._publish_async(tenant_id, subject_id, body),
            name="redis_event_publish",
        )

    async def _publish_async(
        self, tenant_id: str, subject_id: str, body: str
    ) -> None:
        try:
            await self._redis.publish(
                f"timeline:events:{tenant_id}", body
            )
            await self._redis.publish(
                f"timeline:events:{tenant_id}:{subject_id}", body
            )
        except Exception:
            logger.warning(
                "Redis publish failed for tenant=%s subject=%s",
                tenant_id,
                subject_id,
                exc_info=True,
            )

    async def subscribe(
        self, tenant_id: str, subject_id: str | None = None
    ) -> AsyncIterator[dict]:
        """Subscribe to events for tenant (all subjects or one subject)."""
        channel = (
            f"timeline:events:{tenant_id}:{subject_id}"
            if subject_id
            else f"timeline:events:{tenant_id}"
        )
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
