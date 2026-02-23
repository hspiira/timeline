"""Tenant ID format validation for RLS and API.

Shared by dependencies (get_tenant_id) and database (_set_tenant_context)
so invalid tenant IDs are rejected consistently and RLS is never skipped.
"""

import re

# CUID/UUID-style: alphanumeric, hyphen, underscore; max length for SET LOCAL safety.
TENANT_ID_MAX_LENGTH = 64
_TENANT_ID_RE = re.compile(
    r"^[a-zA-Z0-9_-]{1," + str(TENANT_ID_MAX_LENGTH) + r"}$"
)


def is_valid_tenant_id_format(value: str) -> bool:
    """Return True if value is safe for use (e.g. SET LOCAL and header validation)."""
    if not value or len(value) > TENANT_ID_MAX_LENGTH:
        return False
    return bool(_TENANT_ID_RE.fullmatch(value))
