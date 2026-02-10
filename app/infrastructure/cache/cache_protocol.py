"""Cache protocol for repository layer (DIP). Real implementation in Phase 4."""

from typing import Any, Protocol


class CacheProtocol(Protocol):
    """Protocol for cache backends (e.g. Redis). Used by cacheable repositories."""

    def is_available(self) -> bool:
        """Return True if cache is connected and usable."""
        ...

    async def get(self, key: str) -> Any:
        """Return cached value or None."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value with optional TTL in seconds."""
        ...

    async def delete(self, key: str) -> None:
        """Remove key from cache."""
        ...
