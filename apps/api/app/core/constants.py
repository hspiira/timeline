"""Core constants: cache key prefixes and shared literal values.

Single source of truth for cache key structure (DRY). Used by
infrastructure cache and cacheable repositories from Phase 3 onward.
"""

# Cache key prefixes (used with :id or :tenant_id:type:version etc.)
CACHE_PREFIX_TENANT = "tenant"
CACHE_PREFIX_PERMISSION = "permission"
CACHE_PREFIX_SCHEMA = "schema"
CACHE_PREFIX_USER = "user"

# Delimiter for composite keys
CACHE_KEY_SEP = ":"
