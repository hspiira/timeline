"""Reset a user's password (Postgres only).

Usage:
    uv run python -m scripts.reset_password <user_id> <new_password>
All imports use app.*.
"""

import asyncio
import sys

from app.core.config import get_settings
from app.infrastructure.persistence.database import AsyncSessionLocal
from app.infrastructure.persistence.repositories import UserRepository


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

    settings = get_settings()
    if settings.database_backend != "postgres":
        print("This script requires DATABASE_BACKEND=postgres", file=sys.stderr)
        sys.exit(1)
    if AsyncSessionLocal is None:
        print("AsyncSessionLocal not configured", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            user_repo = UserRepository(session, audit_service=None)
            user = await user_repo.update_password(user_id, new_password)
            if not user:
                print(f"User not found: {user_id}", file=sys.stderr)
                sys.exit(1)
            print(f"Password reset for user {user.id} ({user.username})")


if __name__ == "__main__":
    asyncio.run(main())
