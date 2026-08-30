"""User repository with audit and password helpers. Interface methods return application DTOs."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserResult
from app.domain.exceptions import DuplicateEmailException, UserAlreadyExistsException
from app.infrastructure.persistence.models.identity import Identity, normalise_email
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
    """Map a membership plus its identity to UserResult (never the password)."""
    return UserResult(
        id=u.id,
        tenant_id=u.tenant_id,
        username=u.username,
        email=u.identity.email,
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
        """Audit payload: never include the password hash (see docs/AUDIT_AND_PII.md).

        References the identity by id rather than by email, both to keep the address
        out of audit rows and because this runs during insert, before the identity
        relationship is loaded.
        """
        return {
            "id": obj.id,
            "username": obj.username,
            "identity_id": obj.identity_id,
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
        """Find a membership by the person's email within one organisation."""
        result = await self.db.execute(
            select(User)
            .join(Identity, Identity.id == User.identity_id)
            .where(
                Identity.email == normalise_email(email),
                User.tenant_id == tenant_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_organisations_for_email(self, email: str) -> list[tuple[str, str]]:
        """Return (tenant_id, tenant_name) for every organisation this email belongs to.

        Used by the sign-in screen so nobody has to type an organisation code: one
        result goes straight to the password step, several show a name picker.

        This runs before any tenant context exists, and both ``app_user`` and
        ``tenant`` are behind row-level security, so a plain query would return
        nothing. It goes through the ``signin_organisations`` database function
        (migration f4g5h6i7j8k9), which is the single deliberate exception the
        sign-in path gets. The function answers only this one question and returns
        nothing about the person.

        Inactive memberships and suspended organisations are excluded, so an
        organisation someone has been removed from simply stops being offered.
        """
        result = await self.db.execute(
            text("SELECT tenant_id, tenant_name FROM signin_organisations(:email)"),
            {"email": normalise_email(email)},
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_by_id_and_tenant(self, user_id: str, tenant_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def authenticate(
        self, email: str, tenant_id: str, password: str
    ) -> User | None:
        """Verify a password against the person's identity and return their membership.

        The password is checked once, on the identity, so it is the same password
        whichever organisation they are signing in to. Both the identity and the
        membership must be active.
        """
        user = await self.get_by_email_and_tenant(email, tenant_id)
        if not user:
            # Spend the same time as a real check so a missing account is not
            # distinguishable by response time.
            dummy_hash = await _get_dummy_hash()
            await asyncio.to_thread(verify_password, password, dummy_hash)
            return None
        if not user.is_active or not user.identity.is_active:
            return None
        if not await asyncio.to_thread(
            verify_password, password, user.identity.hashed_password
        ):
            return None
        return user

    async def get_by_id(self, user_id: str) -> UserResult | None:
        user = await super().get_entity_by_id(user_id)
        return _user_to_result(user) if user else None

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> UserResult:
        """Add a person to an organisation, creating their identity if they are new.

        If an identity already exists for this email, it is reused and ``password``
        is ignored: the person keeps the one password they already have. That is the
        point of splitting identity from membership — a human has one credential,
        not one per organisation.

        Raises:
            UserAlreadyExistsException: if this person is already in this
                organisation, or the username is taken within it.
        """
        normalised = normalise_email(email)
        existing = await self.db.execute(
            select(Identity).where(Identity.email == normalised)
        )
        identity = existing.scalar_one_or_none()
        if identity is None:
            identity = Identity(
                email=normalised,
                hashed_password=await asyncio.to_thread(get_password_hash, password),
                is_active=True,
            )
            self.db.add(identity)
            await self.db.flush()

        user = User(
            tenant_id=tenant_id,
            username=username,
            identity_id=identity.id,
            is_active=True,
        )
        # Set before create() so the identity is present for result mapping.
        user.identity = identity
        try:
            created = await self.create_entity(user)
        except IntegrityError:
            raise UserAlreadyExistsException()
        return _user_to_result(created)

    async def update(
        self, obj: User, *, skip_existence_check: bool = False
    ) -> User:
        """Update user; raise DuplicateEmailException on unique constraint (e.g. duplicate email)."""
        try:
            return await super().update_entity(obj, skip_existence_check=skip_existence_check)
        except IntegrityError:
            raise DuplicateEmailException()

    async def update_password(self, user_id: str, new_password: str) -> UserResult | None:
        """Change the password on the person's identity, given one of their memberships.

        Because the credential lives on the identity, this changes their password
        everywhere at once rather than in one organisation only.
        """
        user = await super().get_entity_by_id(user_id)
        if not user:
            return None
        user.identity.hashed_password = await asyncio.to_thread(
            get_password_hash, new_password
        )
        await self.db.flush()
        return _user_to_result(user)

    async def deactivate(self, user_id: str, tenant_id: str) -> User | None:
        """Remove this person's access to this organisation only.

        Their identity is untouched, so they keep signing in to any other
        organisation they belong to. Never flip ``identity.is_active`` from a
        tenant-scoped call.
        """
        user = await self.get_by_id_and_tenant(user_id, tenant_id)
        if not user:
            return None
        user.is_active = False
        updated = await self.update_without_audit(user)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return updated

    async def activate(self, user_id: str, tenant_id: str) -> User | None:
        """Restore this person's access to this organisation only."""
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
