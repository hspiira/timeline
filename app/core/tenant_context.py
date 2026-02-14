"""Tenant context for RLS (row-level security).

Middleware sets the current tenant_id in this context variable so that
get_db / get_db_transactional can run SET LOCAL app.current_tenant_id
on the session. When RLS is enabled, only rows for that tenant are visible.
"""

from contextvars import ContextVar

# Current tenant ID for the request (set by middleware, read by DB session setup).
current_tenant_id: ContextVar[str | None] = ContextVar(
    "current_tenant_id", default=None
)


def set_tenant_id(tenant_id: str | None) -> None:
    """Set the current tenant ID for this context (e.g. request)."""
    current_tenant_id.set(tenant_id)


def get_tenant_id() -> str | None:
    """Return the current tenant ID if set."""
    return current_tenant_id.get()
