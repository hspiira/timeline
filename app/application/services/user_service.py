"""User application service: update current user (email/password)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from app.application.dtos.user import UserResult
from app.domain import ValidationException
from app.domain.exceptions import ResourceNotFoundException
from app.shared.utils.email import normalise_email


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

    def __init__(
        self,
        user_repo: Any,
        hash_password: Callable[[str], str],
    ) -> None:
        self._user_repo = user_repo
        self._hash_password = hash_password

    async def update_me(
        self,
        user_id: str,
        tenant_id: str,
        email: str | None = None,
        password: str | None = None,
    ) -> UserResult:
        """Update email and/or password.

        Both live on the person's identity rather than on this organisation's
        membership, so a change here applies wherever they sign in. Email is unique
        system-wide; the repository raises DuplicateEmailException if it is taken.

        Raises:
            ResourceNotFoundException: if the membership does not exist.
            ValidationException: if neither field is supplied.
        """
        if email is None and password is None:
            raise ValidationException("At least one of email or password is required")
        user = await self._user_repo.get_by_id_and_tenant(user_id, tenant_id)
        if not user:
            raise ResourceNotFoundException("user", user_id)
        if email is not None:
            user.identity.email = normalise_email(email)
        if password is not None:
            user.identity.hashed_password = await asyncio.to_thread(
                self._hash_password, password
            )
        updated = await self._user_repo.update(user)
        return _user_to_result(updated)
