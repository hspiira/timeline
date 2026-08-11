"""Create a test user in an existing tenant (Postgres only).

Usage:
    uv run python -m scripts.create_test_user <tenant_code> <username> [password]
If password is omitted, a random one is printed.
All imports use app.*.
"""

import asyncio
import sys

from app.infrastructure.persistence.repositories import TenantRepository, UserRepository
from scripts._session import open_session, resolve_tenant


async def main() -> None:
    """Create test user; tenant identified by code."""
    if len(sys.argv) < 3:
        print(
            "Usage: uv run python -m scripts.create_test_user <tenant_code> <username> [password]",
            file=sys.stderr,
        )
        sys.exit(1)
    tenant_code = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3] if len(sys.argv) > 3 else None

    async with open_session() as session:
        async with session.begin():
            tenant_repo = TenantRepository(
                session, cache_service=None, audit_service=None
            )
            user_repo = UserRepository(session, audit_service=None)
            tenant = await resolve_tenant(session, tenant_repo, tenant_code)
            if not password:
                import secrets

                password = secrets.token_urlsafe(12)
            user = await user_repo.create_user(
                tenant_id=tenant.id,
                username=username,
                email=f"{username}@test.local",
                password=password,
            )
            print(
                f"Created user: {user.id} ({username}) in tenant {tenant.id} ({tenant_code})"
            )
            print(f"Password: {password}")


if __name__ == "__main__":
    asyncio.run(main())
