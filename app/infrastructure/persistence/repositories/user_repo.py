"""User repository with audit and password helpers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.repositories.auditable_repo import AuditableRepository
from app.infrastructure.security.password import get_password_hash, verify_password
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.application.services.system_audit_service import SystemAuditService


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

    def _get_tenant_id(self, obj: User) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: User) -> dict[str, Any]:
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
            verify_password(password, "$2b$12$dummy.hash.to.prevent.timing.attacks")
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> User:
        hashed = await asyncio.to_thread(get_password_hash, password)
        user = User(
            tenant_id=tenant_id,
            username=username,
            email=email,
            hashed_password=hashed,
            is_active=True,
        )
        return await self.create(user)

    async def update_password(self, user_id: str, new_password: str) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.hashed_password = get_password_hash(new_password)
        return await self.update(user)

    async def deactivate(self, user_id: str) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = False
        updated = await self.update(user)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return updated

    async def activate(self, user_id: str) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = True
        updated = await self.update(user)
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
