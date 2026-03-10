"""Rate limiter for event creation (per-tenant sliding window)."""

from __future__ import annotations

import time
from collections import deque
from typing import Protocol


class IRateLimiter(Protocol):
    """Protocol for rate limit checks (e.g. event create per tenant)."""

    async def check(
        self, key: str, limit: int, window_seconds: int
    ) -> bool:
        """Return True if allowed, False if rate limited."""
        ...


class InMemoryRateLimiter:
    """Sliding-window counter per key using a deque of timestamps.

    Single event loop; not thread-safe across processes. Use RedisRateLimiter
    when running multiple workers.
    """

    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = {}

    async def check(
        self, key: str, limit: int, window_seconds: int
    ) -> bool:
        """Return True if under limit, False if rate limited."""
        now = time.monotonic()
        cutoff = now - window_seconds
        if key not in self._windows:
            self._windows[key] = deque()
        q = self._windows[key]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True
