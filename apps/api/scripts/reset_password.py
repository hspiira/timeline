"""Reset a user's password (Postgres only).

Usage:
    uv run python -m scripts.reset_password <user_id> <new_password>
All imports use app.*.
"""

import asyncio
import sys

from app.infrastructure.persistence.repositories import UserRepository
from scripts._session import open_session, resolve_tenant_for_user


async def main() -> None:
    """Reset password for user_id."""
    if len(sys.argv) < 3:
        print(
            "Usage: uv run python -m scripts.reset_password <user_id> <new_password>",
            file=sys.stderr,
        )
        sys.exit(1)
    user_id = sys.argv[1]
    new_password = sys.argv[2]

    async with open_session() as session:
        async with session.begin():
            await resolve_tenant_for_user(session, user_id)
            user_repo = UserRepository(session, audit_service=None)
            user = await user_repo.update_password(user_id, new_password)
            if not user:
                print(f"User not found: {user_id}", file=sys.stderr)
                sys.exit(1)
            print(f"Password reset for user {user.id} ({user.username})")


if __name__ == "__main__":
    asyncio.run(main())
