"""OAuth state repository for authorize/callback CSRF and expiration."""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.oauth_provider_config import OAuthState
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.shared.utils.datetime import utc_now
from app.shared.utils.generators import generate_cuid


class OAuthStateRepository(BaseRepository[OAuthState]):
    """Repository for OAuth state (create, get, consume)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, OAuthState)

    async def get_by_id(self, state_id: str) -> OAuthState | None:
        """Return state row by id."""
        result = await self.db.execute(
            select(OAuthState).where(OAuthState.id == state_id)
        )
        return result.scalar_one_or_none()

    async def create_state(
        self,
        tenant_id: str,
        user_id: str,
        provider_config_id: str,
        return_url: str | None = None,
        expires_in_seconds: int = 600,
    ) -> tuple[OAuthState, str]:
        """Create state row and return (entity, signed_state_string).

        Caller passes signed_state_string to the OAuth provider as the state param.
        """
        state_id = generate_cuid()
        nonce = secrets.token_hex(16)
        from app.infrastructure.external.email.envelope_encryption import (
            OAuthStateManager,
        )

        manager = OAuthStateManager()
        signed_state = manager.create_signed_state(state_id)
        # Store signature part for audit (state is "state_id:signature")
        signature = signed_state.rsplit(":", 1)[-1] if ":" in signed_state else ""
        expires_at = utc_now() + timedelta(seconds=expires_in_seconds)
        state = OAuthState(
            id=state_id,
            tenant_id=tenant_id,
            user_id=user_id,
            provider_config_id=provider_config_id,
            nonce=nonce,
            signature=signature,
            expires_at=expires_at,
            consumed=False,
            return_url=return_url,
        )
        await self.create(state)
        return state, signed_state

    async def consume(self, state_id: str) -> OAuthState | None:
        """Mark state as consumed; return updated state or None."""
        state = await self.get_by_id(state_id)
        if not state or state.consumed:
            return None
        if state.expires_at < utc_now():
            return None
        state.consumed = True
        state.consumed_at = utc_now()
        state.callback_received_at = utc_now()
        await self.update(state)
        return state