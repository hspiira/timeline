"""Redis-based cache service for performance optimization.

Provides async Redis caching with TTL support. Used for authorization
permissions, event schemas, and tenant lookups. Integrates with
app.infrastructure.cache.keys for key format (DRY).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async Redis cache service with TTL support.

    Caches permissions (short TTL), event schemas, and tenant lookups.
    Uses app.core.config for connection settings. Call connect() at
    startup and disconnect() at shutdown.
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        """Initialize cache service.

        Args:
            redis_client: Optional Redis client for testing or DI.
        """
        self.redis = redis_client
        self.settings = get_settings()
        self._connected = False

    async def connect(self) -> None:
        """Establish Redis connection. Call on app startup."""
        if self.redis is None:
            try:
                self.redis = redis.Redis(
                    host=self.settings.redis_host,
                    port=self.settings.redis_port,
                    db=self.settings.redis_db,
                    password=self.settings.redis_password.get_secret_value() if self.settings.redis_password else None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
                await self.redis.ping()
                self._connected = True
                logger.info(
                    "Redis cache connected: %s:%s",
                    self.settings.redis_host,
                    self.settings.redis_port,
                )
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(
                    "Redis connection failed: %s. Cache disabled.",
                    e,
                )
                self._connected = False
                self.redis = None

    async def disconnect(self) -> None:
        """Close Redis connection. Call on app shutdown."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self._connected = False
            logger.info("Redis cache disconnected")

    async def _reconnect(self) -> bool:
        """Attempt to reconnect after disconnect. Returns True if reconnected."""
        if self.redis is None:
            return False
        try:
            await self.redis.close()
        except redis.RedisError:
            pass
        self.redis = None
        self._connected = False
        await self.connect()
        return self._connected

    def is_available(self) -> bool:
        """Return True if Redis is connected and usable."""
        return self._connected and self.redis is not None

    async def get(self, key: str) -> Any | None:
        """Return cached value (JSON-deserialized) or None if missing/unavailable.

        Args:
            key: Cache key (use app.infrastructure.cache.keys builders).

        Returns:
            Cached value or None.
        """
        if not self.is_available() or self.redis is None:
            return None
        try:
            value = await self.redis.get(key)
            if value is not None:
                logger.debug("Cache HIT: %s", key)
                return json.loads(value)
            logger.debug("Cache MISS: %s", key)
            return None
        except (redis.ConnectionError, redis.TimeoutError):
            if await self._reconnect():
                try:
                    value = await self.redis.get(key)
                    if value is not None:
                        return json.loads(value)
                    return None
                except redis.RedisError:
                    logger.exception("Cache get error for key %s after reconnect", key)
                    return None
            logger.warning("Cache get unavailable for key %s (Redis disconnected)", key)
            return None
        except redis.RedisError:
            logger.exception("Cache get error for key %s", key)
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Store value with TTL. Returns True on success.

        Args:
            key: Cache key.
            value: Value to cache (JSON-serializable).
            ttl: Time-to-live in seconds (default 300).

        Returns:
            True if stored, False otherwise.
        """
        if not self.is_available() or self.redis is None:
            return False
        try:
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            logger.debug("Cache SET: %s (TTL: %ss)", key, ttl)
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            if await self._reconnect():
                try:
                    await self.redis.setex(key, ttl, serialized)
                    return True
                except redis.RedisError:
                    pass
            logger.warning("Cache set unavailable for key %s (Redis disconnected)", key)
            return False
        except redis.RedisError:
            logger.exception("Cache set error for key %s", key)
            return False

    async def delete(self, key: str) -> bool:
        """Remove key from cache. Returns True if deleted.

        Args:
            key: Cache key to delete.

        Returns:
            True if deleted, False otherwise.
        """
        if not self.is_available() or self.redis is None:
            return False
        try:
            await self.redis.delete(key)
            logger.debug("Cache DELETE: %s", key)
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            if await self._reconnect():
                try:
                    await self.redis.delete(key)
                    return True
                except redis.RedisError:
                    pass
            return False
        except redis.RedisError:
            logger.exception("Cache delete error for key %s", key)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern using SCAN + batched UNLINK (non-blocking).

        Uses scan_iter to avoid KEYS blocking; collects keys in chunks and
        UNLINKs each chunk to minimize round-trips and keep deletion async on server.

        Args:
            pattern: Redis SCAN match pattern (e.g. permission:tenant-123:*).

        Returns:
            Number of keys deleted.
        """
        if not self.is_available() or self.redis is None:
            return 0
        chunk_size = 500
        deleted = 0
        try:
            chunk: list[str] = []
            async for key in self.redis.scan_iter(match=pattern):
                chunk.append(key)
                if len(chunk) >= chunk_size:
                    async with self.redis.pipeline(transaction=False) as pipe:
                        pipe.unlink(*chunk)
                        results = await pipe.execute()
                    deleted += sum(int(r or 0) for r in results)
                    chunk = []
            if chunk:
                async with self.redis.pipeline(transaction=False) as pipe:
                    pipe.unlink(*chunk)
                    results = await pipe.execute()
                deleted += sum(int(r or 0) for r in results)
            if deleted > 0:
                logger.info("Cache INVALIDATE: %s (%s keys)", pattern, deleted)
            return deleted
        except (redis.ConnectionError, redis.TimeoutError):
            if await self._reconnect():
                return await self.delete_pattern(pattern)
            logger.warning(
                "Cache delete_pattern unavailable for %s (Redis disconnected)", pattern
            )
            return 0
        except redis.RedisError:
            logger.exception("Cache delete_pattern error for %s", pattern)
            return 0

    async def clear_all(self) -> bool:
        """Clear entire cache. Use with caution.

        Returns:
            True if cleared, False otherwise.
        """
        if not self.is_available() or self.redis is None:
            return False
        try:
            await self.redis.flushdb()
            logger.warning("Cache CLEARED: all keys deleted")
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            if await self._reconnect():
                try:
                    await self.redis.flushdb()
                    return True
                except redis.RedisError:
                    pass
            return False
        except redis.RedisError:
            logger.exception("Cache clear error")
            return False


def _resolve_cache(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[CacheService | None, tuple[Any, ...], dict[str, Any]]:
    """Resolve CacheService and args/kwargs for the wrapped function.

    Resolution order: keyword "cache", then args[0].cache, then args[0] if CacheService.
    Callers must pass cache via keyword "cache" (recommended) or as first arg's .cache
    attribute or as the first argument.
    """
    if "cache" in kwargs and isinstance(kwargs.get("cache"), CacheService):
        cache = kwargs["cache"]
        call_kwargs = {k: v for k, v in kwargs.items() if k != "cache"}
        return cache, args, call_kwargs
    if args:
        first = args[0]
        if isinstance(first, CacheService):
            return first, args[1:], kwargs
        cache_attr = getattr(first, "cache", None)
        if isinstance(cache_attr, CacheService):
            return cache_attr, args[1:], kwargs
    return None, args, kwargs


def cached(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to cache async function results in Redis.

    The wrapped function must receive a CacheService in one of these ways:
    - keyword argument "cache" (recommended, e.g. from Depends),
    - first argument has a .cache attribute that is a CacheService,
    - or first argument is the CacheService instance.

    Args:
        key_prefix: Prefix for cache key (e.g. 'permission').
        ttl: Time-to-live in seconds.
        key_builder: Optional callable(args, kwargs) -> key; else built from args/kwargs.

    Returns:
        Decorator that caches return value when CacheService is resolved.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache, func_args, call_kwargs = _resolve_cache(args, kwargs)
            if cache is None:
                return await func(*args, **kwargs)
            if key_builder:
                cache_key = key_builder(*func_args, **call_kwargs)
            else:
                parts = [str(a) for a in func_args]
                parts.extend(f"{k}={v}" for k, v in sorted(call_kwargs.items()))
                cache_key = f"{key_prefix}:{':'.join(parts)}"
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
