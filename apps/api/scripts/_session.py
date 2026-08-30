"""Shared session and tenant-context helpers for the operator scripts.

Two things every script here needs, and every one of them previously got wrong.

**Import the module, not the name.** ``_ensure_engine()`` creates the engine lazily
and rebinds ``AsyncSessionLocal`` as a module global. A ``from ... import
AsyncSessionLocal`` captures the pre-init ``None`` permanently, so the usual
"if AsyncSessionLocal is None: exit" guard fired every time and the scripts refused
to run at all.

**Set the tenant context.** Almost every table is behind row-level security keyed on
``current_setting('app.current_tenant_id')``. Nothing sets that outside an HTTP
request, so a script reads zero rows and writes are rejected — with no error on
reads, which is the dangerous part: a seed script would appear to succeed while
finding nothing.

These scripts are operator tools and are expected to run with the **administrator**
connection string, the same one migrations use. Resolving a tenant by its code has to
read the ``tenant`` table before any tenant is known, which only a role holding
BYPASSRLS can do. :func:`resolve_tenant` therefore fails with an explicit
instruction rather than a confusing "not found" when run with the application role.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import text

# Module import on purpose — see the note above about rebinding.
from app.infrastructure.persistence import database as _database
from app.core.tenant_validation import is_valid_tenant_id_format

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def fail(message: str) -> None:
    """Print an error and exit non-zero."""
    print(message, file=sys.stderr)
    sys.exit(1)


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session, exiting with a clear message if none can be made."""
    _database._ensure_engine()
    if _database.AsyncSessionLocal is None:
        fail(
            "DATABASE_URL is not configured. Set it to the administrator connection "
            "string (the one used for migrations) and try again."
        )
    async with _database.AsyncSessionLocal() as session:
        yield session


async def use_tenant(session: AsyncSession, tenant_id: str) -> None:
    """Point the session's row-level security context at one organisation.

    Lasts for the current transaction, so call it inside the same ``session.begin()``
    block as the work it applies to.
    """
    if not is_valid_tenant_id_format(tenant_id):
        fail(f"Refusing to use a malformed tenant id: {tenant_id!r}")
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))


async def use_tenant_for_connection(session: AsyncSession, tenant_id: str) -> None:
    """Set the tenant context for the whole connection, not just one transaction.

    ``SET LOCAL`` is undone when its transaction ends, which is no use to a caller
    that manages its own transactions internally — ``EventService`` opens one per
    event so it can lock the subject row and retry on a chain fork, and there is no
    way to inject a setting inside it.

    A plain ``SET`` followed by a commit sticks to the connection for as long as the
    session holds it, so those inner transactions inherit it. Only appropriate for a
    single-purpose script session; a request-scoped session must use
    :func:`use_tenant` so nothing leaks between tenants on a pooled connection.
    """
    if not is_valid_tenant_id_format(tenant_id):
        fail(f"Refusing to use a malformed tenant id: {tenant_id!r}")
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
    await session.commit()


async def has_rls_bypass(session: AsyncSession) -> bool:
    """Return whether the connected role can see across organisations."""
    result = await session.execute(
        text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
    )
    return bool(result.scalar())


async def _require_bypass(session: AsyncSession, what: str) -> None:
    """Exit with instructions if the connected role cannot see across organisations."""
    if not await has_rls_bypass(session):
        fail(
            f"Cannot {what} as a database role without BYPASSRLS.\n"
            "This lookup happens before any organisation is known, so it requires the "
            "administrator connection string — the same one used for migrations.\n"
            "Re-run with: DATABASE_URL=<admin connection string> uv run python -m "
            "scripts.<name> ..."
        )


async def resolve_tenant_for_user(session: AsyncSession, user_id: str) -> str:
    """Return the organisation a membership belongs to, and enter its context.

    Used by scripts that identify someone by membership id rather than by
    organisation, such as resetting a password.
    """
    await _require_bypass(session, f"look up membership {user_id!r}")
    result = await session.execute(
        text("SELECT tenant_id FROM app_user WHERE id = :uid"), {"uid": user_id}
    )
    tenant_id = result.scalar()
    if tenant_id is None:
        fail(f"User not found: {user_id}")
    await use_tenant(session, tenant_id)
    return tenant_id


async def resolve_tenant(session: AsyncSession, tenant_repo, code: str):
    """Look up a tenant by code and make the session operate inside it.

    Returns the tenant. Exits with an actionable message if it cannot be seen, since
    the likely cause is running with the application role rather than a genuinely
    missing organisation.
    """
    tenant = await tenant_repo.get_by_code(code)
    if tenant is None:
        if not await has_rls_bypass(session):
            fail(
                f"Cannot look up tenant {code!r} as database role without BYPASSRLS.\n"
                "Reading the tenant table before a tenant is known requires the "
                "administrator connection string — the same one used for migrations.\n"
                "Re-run with: DATABASE_URL=<admin connection string> uv run python -m "
                "scripts.<name> ..."
            )
        fail(f"Tenant not found: {code}")
    await use_tenant(session, tenant.id)
    return tenant
