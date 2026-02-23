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


async def _main() -> int:
    app_role = os.environ.get("VERIFY_RLS_APP_ROLE") or os.environ.get("APP_ROLE")
    migrator_role = os.environ.get("VERIFY_RLS_MIGRATOR_ROLE")
    check_policies = os.environ.get("VERIFY_RLS_POLICIES", "").lower() in (
        "1",
        "true",
        "yes",
    )

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        try:
            from app.core.config import get_settings

            database_url = get_settings().database_url
        except Exception as e:
            print(f"Could not get DATABASE_URL or settings: {e}", file=sys.stderr)
            return 1

    from app.infrastructure.persistence.rls_check import run_rls_check

    result = await run_rls_check(
        database_url=database_url,
        app_role=app_role,
        migrator_role=migrator_role,
        check_policies=check_policies,
    )

    if result.ok:
        print(result.message)
        return 0
    print(result.message, file=sys.stderr)
    return 1


def main() -> None:
    exit_code = asyncio.run(_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
