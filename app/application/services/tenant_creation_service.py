"""Tenant creation: new tenant + admin user + RBAC initialization."""

from __future__ import annotations

import secrets
import string
from typing import TYPE_CHECKING

from app.application.dtos.tenant import TenantCreationResult
from app.application.interfaces.repositories import (
    IPasswordSetTokenStore,
    ITenantRepository,
    IUserRepository,
)
from app.application.interfaces.services import ITenantInitializationService
from app.domain.enums import TenantStatus
from app.domain.exceptions import TenantAlreadyExistsException
from app.shared.enums import ActorType, AuditAction

if TYPE_CHECKING:
    from app.application.interfaces.services import IAuditService


class TenantCreationService:
    """Creates new tenant with admin user and RBAC (permissions, roles, admin assignment)."""

    def __init__(
        self,
        tenant_repo: ITenantRepository,
        user_repo: IUserRepository,
        init_service: ITenantInitializationService,
        audit_service: IAuditService | None = None,
        token_store: IPasswordSetTokenStore | None = None,
    ) -> None:
        self.tenant_repo = tenant_repo
        self.user_repo = user_repo
        self.init_service = init_service
        self.audit_service = audit_service
        self.token_store = token_store

    async def create_tenant(
        self,
        code: str,
        name: str,
        admin_initial_password: str | None = None,
    ) -> TenantCreationResult:
        """Create tenant, init RBAC, create admin user, assign admin role.

        If admin_initial_password is provided, it is used for the admin user;
        otherwise a password is generated (but never returned). Caller must run
        this within a single DB transaction (e.g. use a transactional session
        dependency) so that tenant creation, RBAC init, user creation and role
        assignment are atomic.

        Timeout / cancellation: the whole flow runs in one transaction; on
        request timeout (e.g. 504) the transaction is rolled back and no
        partial tenant is left.
        """
        existing = await self.tenant_repo.get_by_code(code)
        if existing:
            raise TenantAlreadyExistsException(code)

        created_tenant = await self.tenant_repo.create_tenant(
            code=code,
            name=name,
            status=TenantStatus.ACTIVE,
        )
        tenant_id = created_tenant.id

        await self.init_service.initialize_tenant_infrastructure(
            tenant_id=tenant_id,
        )

        password = (
            admin_initial_password
            if admin_initial_password is not None
            else self._generate_secure_password()
        )
        admin_username = "admin"
        admin_email = f"admin@{code}.timeline"
        admin_user = await self.user_repo.create_user(
            tenant_id=tenant_id,
            username=admin_username,
            email=admin_email,
            password=password,
        )

        await self.init_service.assign_admin_role(
            tenant_id=tenant_id,
            admin_user_id=admin_user.id,
        )

        set_password_token: str | None = None
        set_password_expires_at = None
        if self.token_store is not None:
            set_password_token, set_password_expires_at = await self.token_store.create(
                admin_user.id
            )

        if self.audit_service is not None:
            status_value = (
                created_tenant.status.value
                if hasattr(created_tenant.status, "value")
                else str(created_tenant.status)
            )
            await self.audit_service.emit_audit_event(
                tenant_id=tenant_id,
                entity_type="tenant",
                action=AuditAction.CREATED,
                entity_id=tenant_id,
                entity_data={
                    "id": tenant_id,
                    "code": created_tenant.code,
                    "name": created_tenant.name,
                    "status": status_value,
                },
                actor_id=None,
                actor_type=ActorType.SYSTEM,
                metadata=None,
            )

        return TenantCreationResult(
            tenant_id=tenant_id,
            tenant_code=created_tenant.code,
            tenant_name=created_tenant.name,
            admin_username=admin_username,
            admin_email=admin_email,
            set_password_token=set_password_token,
            set_password_expires_at=set_password_expires_at,
        )

    @staticmethod
    def _generate_secure_password(length: int = 16) -> str:
        """Generate cryptographically secure password with guaranteed complexity.

        Ensures at least one lowercase, one uppercase, one digit, and one
        special character; remaining positions filled from full alphabet,
        then shuffled.
        """
        special = "!@#$%^&*-_=+"
        alphabet = string.ascii_letters + string.digits + special
        rng = secrets.SystemRandom()
        # Guarantee one of each required class
        chars = [
            rng.choice(string.ascii_lowercase),
            rng.choice(string.ascii_uppercase),
            rng.choice(string.digits),
            rng.choice(special),
        ]
        # Fill the rest from full alphabet
        remaining = max(0, length - 4)
        chars.extend(rng.choice(alphabet) for _ in range(remaining))
        rng.shuffle(chars)
        return "".join(chars)
