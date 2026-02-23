"""Shared constants for dependency modules (tenant cache, etc.)."""

# Short TTL for tenant-ID validation cache (reduce DB load; avoid long-lived negative cache).
TENANT_VALIDATION_CACHE_TTL = 60
TENANT_CACHE_MISS_MARKER = "__missing__"
