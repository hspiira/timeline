"""One-time password-set token store (Postgres). Used for C2 tenant creation flow."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.password_set_token import PasswordSetToken

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
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._ttl_seconds)
        row = PasswordSetToken(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            used_at=None,
        )
        self._session.add(row)
        await self._session.flush()
        return (raw, expires_at)

    async def redeem(self, token: str) -> str | None:
        """If token is valid and not expired/used, mark used and return user_id; else None."""
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(PasswordSetToken)
            .where(PasswordSetToken.token_hash == token_hash)
            .where(PasswordSetToken.used_at.is_(None))
            .where(PasswordSetToken.expires_at > now)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        row.used_at = now
        await self._session.flush()
        return row.user_id