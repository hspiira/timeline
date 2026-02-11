"""User application service: update current user (email/password)."""

from __future__ import annotations

import asyncio
from typing import Any

from app.application.dtos.user import UserResult


def _user_to_result(u: Any) -> UserResult:
    """Build UserResult from user entity."""
    return UserResult(
        id=u.id,
        tenant_id=u.tenant_id,
        username=u.username,
        email=u.email,
        is_active=u.is_active,
    )


class UserService:
    """Update current user profile (email, password)."""

    def __init__(self, user_repo: Any, auth_security: Any) -> None:
        self._user_repo = user_repo
        self._auth_security = auth_security

    async def update_me(
        self,
        user_id: str,
        tenant_id: str,
        email: str | None = None,
        password: str | None = None,
    ) -> UserResult:
        """Update email and/or password. Raises ValueError if user not found."""
        user = await self._user_repo.get_by_id_and_tenant(user_id, tenant_id)
        if not user:
            raise ValueError("User not found")
        if email is not None:
            user.email = email
        if password is not None:
            user.hashed_password = await asyncio.to_thread(
                self._auth_security.hash_password, password
            )
        updated = await self._user_repo.update(user)
        return _user_to_result(updated)
