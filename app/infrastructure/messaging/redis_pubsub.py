"""Redis Pub/Sub for real-time sync progress events.

Publishes and subscribes to email sync progress per tenant. Used by
email sync flows and WebSocket to push progress to clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class SyncStage(str, Enum):
    """Stages of email sync progress."""

    STARTED = "started"
    FETCHING = "fetching_messages"
    PROCESSING = "processing_messages"
    SAVING = "saving_events"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncProgressEvent:
    """Sync progress event payload for Redis."""

    account_id: str
    email_address: str
    stage: SyncStage
    message: str
    timestamp: str
    messages_fetched: int = 0
    events_created: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON publish."""
        data = asdict(self)
        data["stage"] = self.stage.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncProgressEvent:
        """Deserialize from Redis message."""
        data = dict(data)
        data["stage"] = SyncStage(data["stage"])
        return cls(**data)


class _RedisPubSubBase:
    """Shared Redis connection and channel logic for sync progress pub/sub."""

    CHANNEL_PREFIX = "sync_progress"

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        """Initialize. Pass redis_client for DI/testing."""
        self.redis = redis_client
        self.settings = get_settings()
        self._connected = redis_client is not None

    async def connect(self) -> None:
        """Establish Redis connection. Call on app startup."""
        if self._connected:
            return
        if self.redis is None:
            try:
                self.redis = redis.Redis(
                    host=self.settings.redis_host,
                    port=self.settings.redis_port,
                    db=self.settings.redis_db,
                    password=self.settings.redis_password.get_secret_value() if self.settings.redis_password else None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                await self.redis.ping()
                self._connected = True
                logger.info("Redis pub/sub connected")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning("Redis pub/sub connection failed: %s", e)
                self._connected = False
                self.redis = None

    async def disconnect(self) -> None:
        """Close Redis connection. Call on app shutdown."""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Redis pub/sub disconnected")

    def is_available(self) -> bool:
        """Return True if Redis is connected."""
        return self._connected and self.redis is not None

    def _get_channel(self, tenant_id: str) -> str:
        """Channel name for tenant."""
        return f"{self.CHANNEL_PREFIX}:{tenant_id}"


class SyncProgressPublisher(_RedisPubSubBase):
    """Publishes sync progress events to Redis per-tenant channel."""

    async def publish(self, tenant_id: str, event: SyncProgressEvent) -> bool:
        """Publish sync progress event to tenant channel.

        Args:
            tenant_id: Tenant ID.
            event: Progress event.

        Returns:
            True if published, False if Redis unavailable.
        """
        if not self.is_available() or self.redis is None:
            logger.debug("Redis not available, skipping publish")
            return False
        try:
            channel = self._get_channel(tenant_id)
            message = json.dumps(event.to_dict())
            await self.redis.publish(channel, message)
            logger.debug(
                "Published sync progress to %s: %s", channel, event.stage.value
            )
        except Exception:
            logger.exception("Failed to publish sync progress")
            return False
        else:
            return True

    async def publish_started(
        self,
        tenant_id: str,
        account_id: str,
        email_address: str,
    ) -> bool:
        """Publish sync started."""
        event = SyncProgressEvent(
            account_id=account_id,
            email_address=email_address,
            stage=SyncStage.STARTED,
            message="Sync started",
            timestamp=utc_now().isoformat(),
        )
        return await self.publish(tenant_id, event)

    async def publish_fetching(
        self,
        tenant_id: str,
        account_id: str,
        email_address: str,
    ) -> bool:
        """Publish fetching messages."""
        event = SyncProgressEvent(
            account_id=account_id,
            email_address=email_address,
            stage=SyncStage.FETCHING,
            message="Fetching messages from provider",
            timestamp=utc_now().isoformat(),
        )
        return await self.publish(tenant_id, event)

    async def publish_processing(
        self,
        tenant_id: str,
        account_id: str,
        email_address: str,
        messages_fetched: int,
    ) -> bool:
        """Publish processing messages."""
        event = SyncProgressEvent(
            account_id=account_id,
            email_address=email_address,
            stage=SyncStage.PROCESSING,
            message=f"Processing {messages_fetched} messages",
            timestamp=utc_now().isoformat(),
            messages_fetched=messages_fetched,
        )
        return await self.publish(tenant_id, event)

    async def publish_saving(
        self,
        tenant_id: str,
        account_id: str,
        email_address: str,
        messages_fetched: int,
        events_created: int,
    ) -> bool:
        """Publish saving events."""
        event = SyncProgressEvent(
            account_id=account_id,
            email_address=email_address,
            stage=SyncStage.SAVING,
            message=f"Saving {events_created} new events",
            timestamp=utc_now().isoformat(),
            messages_fetched=messages_fetched,
            events_created=events_created,
        )
        return await self.publish(tenant_id, event)

    async def publish_completed(
        self,
        tenant_id: str,
        account_id: str,
        email_address: str,
        messages_fetched: int,
        events_created: int,
    ) -> bool:
        """Publish sync completed."""
        event = SyncProgressEvent(
            account_id=account_id,
            email_address=email_address,
            stage=SyncStage.COMPLETED,
            message="Sync completed successfully",
            timestamp=utc_now().isoformat(),
            messages_fetched=messages_fetched,
            events_created=events_created,
        )
        return await self.publish(tenant_id, event)

    async def publish_failed(
        self,
        tenant_id: str,
        account_id: str,
        email_address: str,
        error: str,
    ) -> bool:
        """Publish sync failed."""
        event = SyncProgressEvent(
            account_id=account_id,
            email_address=email_address,
            stage=SyncStage.FAILED,
            message="Sync failed",
            timestamp=utc_now().isoformat(),
            error=error,
        )
        return await self.publish(tenant_id, event)


class SyncProgressSubscriber(_RedisPubSubBase):
    """Subscribes to sync progress events from Redis.

    subscribe() is reentrant: each call uses a locally-scoped PubSub that is
    closed in finally, so multiple tenants or concurrent subscriptions are safe.
    """

    async def subscribe(self, tenant_id: str) -> AsyncIterator[SyncProgressEvent]:
        """Subscribe to sync progress for a tenant. Yields events as they arrive."""
        if not self.is_available() or self.redis is None:
            logger.warning("Redis not available for subscription")
            return
        channel = self._get_channel(tenant_id)
        pubsub = self.redis.pubsub()
        try:
            await pubsub.subscribe(channel)
            logger.info("Subscribed to %s", channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield SyncProgressEvent.from_dict(data)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        logger.exception("Failed to parse sync progress message")
        except Exception:
            logger.exception("Subscription error")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            logger.info("Unsubscribed from %s", channel)


async def run_sync_progress_broadcast(app: Any) -> None:
    """Subscribe to Redis sync_progress:* and broadcast each message to the tenant's WebSocket connections.

    Call as a background task from lifespan when Redis is enabled. Cancelling the task stops the loop.
    """

    subscriber = SyncProgressSubscriber()
    await subscriber.connect()
    if not subscriber.is_available() or subscriber.redis is None:
        logger.warning("Redis not available, sync progress broadcast not started")
        return
    pubsub = subscriber.redis.pubsub()
    try:
        await pubsub.psubscribe(f"{SyncProgressSubscriber.CHANNEL_PREFIX}:*")
        logger.info("Subscribed to %s:* for WebSocket broadcast", SyncProgressSubscriber.CHANNEL_PREFIX)
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            channel = message.get("channel")
            try:
                channel_str = channel.decode() if isinstance(channel, bytes) else (channel or "")
            except Exception:
                channel_str = str(channel) if channel else ""
            if not channel_str or ":" not in channel_str:
                continue
            tenant_id = channel_str.split(":", 1)[1]
            try:
                data = json.loads(message["data"])
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.exception("Failed to parse sync progress message")
                continue
            payload = {**data, "type": "sync_progress"}
            manager = getattr(app.state, "ws_manager", None)
            if manager is not None:
                await manager.broadcast_to_tenant(tenant_id, payload)
    except asyncio.CancelledError:
        logger.info("Sync progress broadcast task cancelled")
    except Exception:
        logger.exception("Sync progress broadcast error")
    finally:
        await pubsub.punsubscribe()
        await pubsub.close()


_publisher: SyncProgressPublisher | None = None


def get_sync_publisher() -> SyncProgressPublisher | None:
    """Return the global sync progress publisher (set at startup)."""
    return _publisher


def set_sync_publisher(publisher: SyncProgressPublisher) -> None:
    """Set the global sync progress publisher."""
    global _publisher
    _publisher = publisher
