"""Redis-backed rate limiter (sliding window). Shared across workers."""

from __future__ import annotations

import logging
import time
import uuid

import redis.asyncio as redis

from app.application.services.rate_limiter import IRateLimiter

KEY_PREFIX = "rl:"

logger = logging.getLogger(__name__)

# Atomic sliding-window: remove expired, count, add if under limit.
# ARGV: limit, window_end, window_seconds, member, score (now)
_LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_end = tonumber(ARGV[2])
local window_seconds = tonumber(ARGV[3])
local member = ARGV[4]
local score = tonumber(ARGV[5])
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_end)
local count = redis.call('ZCARD', key)
if count >= limit then
  return 0
end
redis.call('ZADD', key, score, member)
redis.call('EXPIRE', key, window_seconds + 1)
return 1
"""


class RedisRateLimiter:
    """Sliding-window rate limiter using Redis sorted sets.

    Safe for multi-worker deployments: all workers share the same window.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize with an async Redis client (e.g. from CacheService)."""
        self._redis = redis_client
        self._script = self._redis.register_script(_LUA_SLIDING_WINDOW)

    async def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Return True if under limit, False if rate limited."""
        redis_key = f"{KEY_PREFIX}{key}"
        now = time.time()
        window_end = now - window_seconds
        member = str(uuid.uuid4())
        try:
            allowed = await self._script(
                keys=[redis_key],
                args=[limit, window_end, window_seconds, member, now],
            )
            return allowed in (1, "1")
        except redis.RedisError as err:
            # Backend failure: log and fail closed so we don't silently disable protection.
            logger.error(
                "RedisRateLimiter backend error for key=%s: %s",
                redis_key,
                err,
                exc_info=True,
            )
            return False
