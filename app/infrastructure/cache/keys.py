"""Cache key builders. Single place for key format (DRY).

Key components (tenant_id, event_type, user_id, etc.) must not contain
CACHE_KEY_SEP to avoid ambiguous or colliding keys.
"""

from app.core.constants import (
    CACHE_KEY_SEP,
    CACHE_PREFIX_PERMISSION,
    CACHE_PREFIX_SCHEMA,
    CACHE_PREFIX_TENANT,
    CACHE_PREFIX_USER,
)


def _validate_key_component(value: str, name: str) -> None:
    """Raise ValueError if value contains the cache key separator.

    Args:
        value: String component used in a cache key.
        name: Name of the component (for error message).

    Raises:
        ValueError: If value contains CACHE_KEY_SEP.
    """
    if CACHE_KEY_SEP in value:
        raise ValueError(
            f"Cache key component {name!r} must not contain separator {CACHE_KEY_SEP!r}"
        )


def _validate_key_components(components: list[tuple[str, str]]) -> None:
    """Validate multiple key components; raise on first invalid one.

    Args:
        components: List of (value, name) pairs to validate.

    Raises:
        ValueError: If any value contains CACHE_KEY_SEP.
    """
    for value, name in components:
        _validate_key_component(value, name)


def tenant_key(tenant_id: str) -> str:
    """Cache key for tenant by ID."""
    _validate_key_component(tenant_id, "tenant_id")
    return f"{CACHE_PREFIX_TENANT}{CACHE_KEY_SEP}id{CACHE_KEY_SEP}{tenant_id}"


def tenant_code_key(code: str) -> str:
    """Cache key for tenant by code."""
    _validate_key_component(code, "code")
    return f"{CACHE_PREFIX_TENANT}{CACHE_KEY_SEP}code{CACHE_KEY_SEP}{code}"


def permission_key(tenant_id: str, user_id: str) -> str:
    """Cache key for user permissions (tenant + user)."""
    _validate_key_components([(tenant_id, "tenant_id"), (user_id, "user_id")])
    return (
        f"{CACHE_PREFIX_PERMISSION}{CACHE_KEY_SEP}{tenant_id}{CACHE_KEY_SEP}{user_id}"
    )


def schema_key(tenant_id: str, event_type: str, version: int) -> str:
    """Cache key for event schema by tenant, event_type, version."""
    _validate_key_components([(tenant_id, "tenant_id"), (event_type, "event_type")])
    return (
        f"{CACHE_PREFIX_SCHEMA}{CACHE_KEY_SEP}{tenant_id}{CACHE_KEY_SEP}"
        f"{event_type}{CACHE_KEY_SEP}{version}"
    )


def schema_active_key(tenant_id: str, event_type: str) -> str:
    """Cache key for active event schema (tenant + event_type)."""
    _validate_key_components([(tenant_id, "tenant_id"), (event_type, "event_type")])
    return f"{CACHE_PREFIX_SCHEMA}{CACHE_KEY_SEP}active{CACHE_KEY_SEP}{tenant_id}{CACHE_KEY_SEP}{event_type}"


def user_key(user_id: str) -> str:
    """Cache key for user by ID."""
    _validate_key_component(user_id, "user_id")
    return f"{CACHE_PREFIX_USER}{CACHE_KEY_SEP}id{CACHE_KEY_SEP}{user_id}"
