"""Rate limiter for event creation (per-tenant sliding window).

Application layer defines the protocol only. Implementations (e.g. Redis-backed
shared-store) live in app.infrastructure and are wired at composition root.
"""

from __future__ import annotations

from typing import Protocol


class IRateLimiter(Protocol):
    """Protocol for rate limit checks (e.g. event create per tenant)."""

    async def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Return True if allowed, False if rate limited."""
        ...
