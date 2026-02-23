"""Verify RLS role configuration: app role must NOT have BYPASSRLS; migrator role must have it.

Usage:
    APP_ROLE=timeline_app uv run python -m scripts.verify_rls_roles
    VERIFY_RLS_MIGRATOR_ROLE=timeline_migrator APP_ROLE=timeline_app uv run python -m scripts.verify_rls_roles
    VERIFY_RLS_POLICIES=1 uv run python -m scripts.verify_rls_roles   # also check that tenant_isolation policies exist

Reads DATABASE_URL from environment (or app.core.config). APP_ROLE defaults to the
user from DATABASE_URL. Exits 0 if checks pass, 1 otherwise.
"""

from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import urlparse


async def _main() -> int:
    app_role = os.environ.get("VERIFY_RLS_APP_ROLE") or os.environ.get("APP_ROLE")
    migrator_role = os.environ.get("VERIFY_RLS_MIGRATOR_ROLE")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        try:
            from app.core.config import get_settings
            settings = get_settings()
            if settings.database_backend != "postgres":
                print("DATABASE_BACKEND is not postgres", file=sys.stderr)
                return 1
            database_url = settings.database_url
        except Exception as e:
            print(f"Could not get DATABASE_URL or settings: {e}", file=sys.stderr)
            return 1

    if not app_role:
        # Parse user from URL: postgresql+asyncpg://user:pass@host/db -> user
        parsed = urlparse(database_url)
        if parsed.username:
            app_role = parsed.username
        else:
            print("Set APP_ROLE or VERIFY_RLS_APP_ROLE (or ensure DATABASE_URL has user)", file=sys.stderr)
            return 1

    # asyncpg expects postgresql:// (no +asyncpg)
    conn_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        import asyncpg
    except ImportError:
        print("asyncpg is required: uv sync", file=sys.stderr)
        return 1

    try:
        conn = await asyncpg.connect(conn_url)
    except Exception as e:
        print(f"Failed to connect: {e}", file=sys.stderr)
        return 1

    try:
        # Check app role: must NOT have BYPASSRLS
        row = await conn.fetchrow(
            "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = $1",
            app_role,
        )
        if not row:
            print(f"Role not found: {app_role}", file=sys.stderr)
            return 1
        if row["rolbypassrls"]:
            print(
                f"RLS check failed: app role '{app_role}' has BYPASSRLS (should not). "
                "Run: ALTER ROLE " + app_role + " NOBYPASSRLS;",
                file=sys.stderr,
            )
            return 1

        if migrator_role:
            mrow = await conn.fetchrow(
                "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = $1",
                migrator_role,
            )
            if not mrow:
                print(f"Migrator role not found: {migrator_role}", file=sys.stderr)
                return 1
            if not mrow["rolbypassrls"]:
                print(
                    f"RLS check failed: migrator role '{migrator_role}' does not have BYPASSRLS. "
                    "Run: ALTER ROLE " + migrator_role + " BYPASSRLS;",
                    file=sys.stderr,
                )
                return 1

        # Optional: verify that tenant_isolation policies exist (avoids false sense of security)
        if os.environ.get("VERIFY_RLS_POLICIES", "").lower() in ("1", "true", "yes"):
            n = await conn.fetchval(
                "SELECT count(*) FROM pg_policies WHERE policyname = $1",
                "tenant_isolation",
            )
            if n is None or n == 0:
                print(
                    "RLS check failed: no tenant_isolation policies found. "
                    "Ensure RLS migration (e.g. w1x2y3z4a5b6) has been applied.",
                    file=sys.stderr,
                )
                return 1

        print("RLS role checks passed.")
        return 0
    finally:
        await conn.close()


def main() -> None:
    exit_code = asyncio.run(_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
