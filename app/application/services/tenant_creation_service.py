"""Tenant creation: new tenant + admin user + RBAC initialization."""

from __future__ import annotations

import secrets
import string

from app.application.dtos.tenant import TenantCreationResult
from app.application.interfaces.repositories import ITenantRepository, IUserRepository
from app.application.interfaces.services import ITenantInitializationService
from app.domain.enums import TenantStatus
from app.domain.exceptions import TenantAlreadyExistsException


class TenantCreationService:
    """Creates new tenant with admin user and RBAC (permissions, roles, admin assignment)."""

    def __init__(
        self,
        tenant_repo: ITenantRepository,
        user_repo: IUserRepository,
        init_service: ITenantInitializationService,
    ) -> None:
        self.tenant_repo = tenant_repo
        self.user_repo = user_repo
        self.init_service = init_service

    async def create_tenant(self, code: str, name: str) -> TenantCreationResult:
        """Create tenant, init RBAC, create admin user, assign admin role.

        Admin password is always auto-generated and returned in the result.
        Caller must run this within a single DB transaction (e.g. use a
        transactional session dependency) so that tenant creation, RBAC init,
        user creation and role assignment are atomic.

        Timeout / cancellation:
        - Postgres: the whole flow runs in one transaction; on request timeout
          (e.g. 504) the transaction is rolled back and no partial tenant is left.
        - Firestore: each write commits immediately. If the request times out
          mid-flow, you can get partial state (e.g. tenant + some permissions
          but no admin user). Retrying with the same code will then fail with
          "tenant already exists". Consider increasing timeout for this
          endpoint or cleaning up orphaned tenant docs if needed.
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

        password = self._generate_secure_password()
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

        return TenantCreationResult(
            tenant_id=tenant_id,
            tenant_code=created_tenant.code,
            tenant_name=created_tenant.name,
            admin_username=admin_username,
            admin_password=password,
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
