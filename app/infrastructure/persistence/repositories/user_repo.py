"""User repository with audit and password helpers. Interface methods return application DTOs."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserResult
from app.domain.exceptions import DuplicateEmailException, UserAlreadyExistsException
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.infrastructure.security.password import get_password_hash, verify_password
from app.shared.enums import AuditAction

# Lazy dummy hash for constant-time comparison when user is not found (timing-attack mitigation).
# Computed on first use in a thread to avoid blocking the event loop at import.
_dummy_hash_cache: str | None = None


async def _get_dummy_hash() -> str:
    """Return a valid bcrypt hash for dummy comparison; computed once in thread pool."""
    global _dummy_hash_cache
    if _dummy_hash_cache is None:
        _dummy_hash_cache = await asyncio.to_thread(
            get_password_hash, "not-a-real-password"
        )
    return _dummy_hash_cache

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _user_to_result(u: User) -> UserResult:
    """Map ORM User to application UserResult (no password)."""
    return UserResult(
        id=u.id,
        tenant_id=u.tenant_id,
        username=u.username,
        email=u.email,
        is_active=u.is_active,
    )


class UserRepository(AuditableRepository[User]):
    """User repository. Authenticate, create_user, update_password, activate/deactivate."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, User, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "user"

    def _serialize_for_audit(self, obj: User) -> dict[str, Any]:
        """Audit payload: never include password_hash or other secrets (see docs/AUDIT_AND_PII.md)."""
        return {
            "id": obj.id,
            "username": obj.username,
            "email": obj.email,
            "is_active": obj.is_active,
        }

    async def get_by_username_and_tenant(
        self, username: str, tenant_id: str
    ) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.username == username,
                User.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_tenant(self, email: str, tenant_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_tenant(self, user_id: str, tenant_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def authenticate(
        self, username: str, tenant_id: str, password: str
    ) -> User | None:
        user = await self.get_by_username_and_tenant(username, tenant_id)
        if not user:
            dummy_hash = await _get_dummy_hash()
            await asyncio.to_thread(verify_password, password, dummy_hash)
            return None
        if not user.is_active:
            return None
        if not await asyncio.to_thread(verify_password, password, user.hashed_password):
            return None
        return user

    async def get_by_id(self, user_id: str) -> UserResult | None:
        user = await super().get_by_id(user_id)
        return _user_to_result(user) if user else None

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> UserResult:
        """Create user; raise UserAlreadyExistsException on unique constraint violation."""
        hashed = await asyncio.to_thread(get_password_hash, password)
        user = User(
            tenant_id=tenant_id,
            username=username,
            email=email,
            hashed_password=hashed,
            is_active=True,
        )
        try:
            created = await self.create(user)
            return _user_to_result(created)
        except IntegrityError:
            raise UserAlreadyExistsException()

    async def update(
        self, obj: User, *, skip_existence_check: bool = False
    ) -> User:
        """Update user; raise DuplicateEmailException on unique constraint (e.g. duplicate email)."""
        try:
            return await super().update(obj, skip_existence_check=skip_existence_check)
        except IntegrityError:
            raise DuplicateEmailException()

    async def update_password(self, user_id: str, new_password: str) -> User | None:
        user = await super().get_by_id(user_id)
        if not user:
            return None
        user.hashed_password = await asyncio.to_thread(get_password_hash, new_password)
        return await self.update(user)

    async def deactivate(self, user_id: str, tenant_id: str) -> User | None:
        user = await self.get_by_id_and_tenant(user_id, tenant_id)
        if not user:
            return None
        user.is_active = False
        updated = await self.update_without_audit(user)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return updated

    async def activate(self, user_id: str, tenant_id: str) -> User | None:
        user = await self.get_by_id_and_tenant(user_id, tenant_id)
        if not user:
            return None
        user.is_active = True
        updated = await self.update_without_audit(user)
        await self.emit_custom_audit(updated, AuditAction.ACTIVATED)
        return updated

    async def get_users_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())
