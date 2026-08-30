"""One-time password-set token store (Postgres). Used for C2 tenant creation flow."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.password_set_token import PasswordSetToken
from app.shared.utils.datetime import utc_now

# Default TTL for set-password link (e.g. 24 hours)
DEFAULT_TOKEN_TTL_SECONDS = 24 * 3600


class PasswordSetTokenStore:
    """Create and redeem one-time tokens for setting initial admin password. Postgres only."""

    def __init__(
        self,
        session: AsyncSession,
        ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    ) -> None:
        self._session = session
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, user_id: str) -> tuple[str, datetime]:
        """Create a one-time token for user; return (raw_token, expires_at)."""
        raw = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw)
        expires_at = utc_now() + timedelta(seconds=self._ttl_seconds)
        row = PasswordSetToken(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            used_at=None,
        )
        self._session.add(row)
        await self._session.flush()
        return (raw, expires_at)

    async def redeem(self, token: str) -> tuple[str, str] | None:
        """Claim a valid, unused, unexpired token. Return (user_id, tenant_id) or None.

        Goes through the ``redeem_password_set_token`` database function (migration
        h6i7j8k9l0m1) rather than querying directly. Setting an initial password
        happens before sign-in, so there is no tenant context, and
        ``password_set_token`` is behind row-level security — a direct read finds
        nothing and a valid link looks expired.

        The function also claims the token in one statement, so two simultaneous
        redemptions cannot both succeed. The tenant id comes back so the caller can
        establish tenant context for the password write that follows.
        """
        result = await self._session.execute(
            text(
                "SELECT user_id, tenant_id FROM redeem_password_set_token(:token_hash)"
            ),
            {"token_hash": self._hash_token(token)},
        )
        row = result.first()
        return (row[0], row[1]) if row else None