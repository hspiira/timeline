"""Shared RLS (row-level security) check for Postgres.

Used by the readiness endpoint and by scripts/verify_rls_roles.
Returns a result object; does not print or exit. Caller decides
whether to fail startup, return 503, or exit with code 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class RLSCheckResult:
    """Result of running RLS checks against Postgres."""

    ok: bool
    message: str


async def run_rls_check(
    database_url: str,
    app_role: str | None = None,
    migrator_role: str | None = None,
    check_policies: bool = False,
) -> RLSCheckResult:
    """Run RLS role and optional policy checks.

    Args:
        database_url: Postgres URL (postgresql:// or postgresql+asyncpg://).
        app_role: Role used by the application; must NOT have BYPASSRLS.
            If None, derived from database_url username.
        migrator_role: If set, this role must have BYPASSRLS.
        check_policies: If True, require at least one tenant_isolation policy.

    Returns:
        RLSCheckResult with ok=True if all checks pass, ok=False and message otherwise.
    """
    if not app_role:
        parsed = urlparse(database_url)
        if parsed.username:
            app_role = parsed.username
        else:
            return RLSCheckResult(
                ok=False,
                message="App role not set and could not derive from DATABASE_URL (no username).",
            )

    conn_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        import asyncpg
    except ImportError:
        return RLSCheckResult(
            ok=False,
            message="asyncpg is required for RLS check. Install with: uv sync",
        )

    try:
        conn = await asyncpg.connect(conn_url)
    except Exception as e:
        return RLSCheckResult(ok=False, message=f"Failed to connect: {e}")

    try:
        row = await conn.fetchrow(
            "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = $1",
            app_role,
        )
        if not row:
            return RLSCheckResult(ok=False, message=f"Role not found: {app_role}")
        if row["rolbypassrls"]:
            return RLSCheckResult(
                ok=False,
                message=(
                    f"RLS check failed: app role '{app_role}' has BYPASSRLS (should not). "
                    f"Run: ALTER ROLE {app_role} NOBYPASSRLS;"
                ),
            )

        if migrator_role:
            mrow = await conn.fetchrow(
                "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = $1",
                migrator_role,
            )
            if not mrow:
                return RLSCheckResult(
                    ok=False,
                    message=f"Migrator role not found: {migrator_role}",
                )
            if not mrow["rolbypassrls"]:
                return RLSCheckResult(
                    ok=False,
                    message=(
                        f"RLS check failed: migrator role '{migrator_role}' does not have BYPASSRLS. "
                        f"Run: ALTER ROLE {migrator_role} BYPASSRLS;"
                    ),
                )

        if check_policies:
            n = await conn.fetchval(
                "SELECT count(*) FROM pg_policies WHERE policyname = $1",
                "tenant_isolation",
            )
            if n is None or n == 0:
                return RLSCheckResult(
                    ok=False,
                    message=(
                        "RLS check failed: no tenant_isolation policies found. "
                        "Ensure RLS migration (e.g. w1x2y3z4a5b6) has been applied."
                    ),
                )

        return RLSCheckResult(ok=True, message="RLS checks passed.")
    finally:
        await conn.close()
