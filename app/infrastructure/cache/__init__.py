"""Cache: Redis service and cache key utilities.

Used by repositories and services for performance (e.g. tenant/schema lookups).
CacheService uses app.core.config; key format is in keys.py (DRY).
"""

from app.infrastructure.cache.cache_protocol import CacheProtocol
from app.infrastructure.cache.keys import (
    permission_key,
    schema_active_key,
    schema_key,
    tenant_code_key,
    tenant_key,
    user_key,
)
from app.infrastructure.cache.redis_cache import CacheService, cached

__all__ = [
    "CacheProtocol",
    "CacheService",
    "cached",
    "permission_key",
    "schema_active_key",
    "schema_key",
    "tenant_code_key",
    "tenant_key",
    "user_key",
]
