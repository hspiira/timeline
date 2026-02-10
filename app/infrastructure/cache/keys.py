"""Cache key builders. Single place for key format (DRY)."""

from app.core.constants import (
    CACHE_KEY_SEP,
    CACHE_PREFIX_PERMISSION,
    CACHE_PREFIX_SCHEMA,
    CACHE_PREFIX_TENANT,
    CACHE_PREFIX_USER,
)


def tenant_key(tenant_id: str) -> str:
    """Cache key for tenant by ID."""
    return f"{CACHE_PREFIX_TENANT}{CACHE_KEY_SEP}id{CACHE_KEY_SEP}{tenant_id}"


def tenant_code_key(code: str) -> str:
    """Cache key for tenant by code."""
    return f"{CACHE_PREFIX_TENANT}{CACHE_KEY_SEP}code{CACHE_KEY_SEP}{code}"


def permission_key(tenant_id: str, user_id: str) -> str:
    """Cache key for user permissions (tenant + user)."""
    return (
        f"{CACHE_PREFIX_PERMISSION}{CACHE_KEY_SEP}{tenant_id}{CACHE_KEY_SEP}{user_id}"
    )


def schema_key(tenant_id: str, event_type: str, version: int) -> str:
    """Cache key for event schema by tenant, event_type, version."""
    return (
        f"{CACHE_PREFIX_SCHEMA}{CACHE_KEY_SEP}{tenant_id}{CACHE_KEY_SEP}"
        f"{event_type}{CACHE_KEY_SEP}{version}"
    )


def schema_active_key(tenant_id: str, event_type: str) -> str:
    """Cache key for active event schema (tenant + event_type)."""
    return f"{CACHE_PREFIX_SCHEMA}{CACHE_KEY_SEP}active{CACHE_KEY_SEP}{tenant_id}{CACHE_KEY_SEP}{event_type}"


def user_key(user_id: str) -> str:
    """Cache key for user by ID."""
    return f"{CACHE_PREFIX_USER}{CACHE_KEY_SEP}id{CACHE_KEY_SEP}{user_id}"
