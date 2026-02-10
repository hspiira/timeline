"""Tenant creation: new tenant + admin user + RBAC initialization."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass

from app.application.interfaces.repositories import ITenantRepository, IUserRepository
from app.application.interfaces.services import ITenantInitializationService
from app.domain.enums import TenantStatus


@dataclass
class TenantCreationResult:
    """Result of tenant creation."""

    tenant_id: str
    tenant_code: str
    tenant_name: str
    admin_username: str
    admin_password: str


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

    async def create_tenant(
        self,
        code: str,
        name: str,
        admin_password: str | None = None,
    ) -> TenantCreationResult:
        """Create tenant, init RBAC, create admin user, assign admin role."""
        created_tenant = await self.tenant_repo.create_tenant(
            code=code,
            name=name,
            status=TenantStatus.ACTIVE.value,
        )
        tenant_id = created_tenant.id

        await self.init_service.initialize_tenant_infrastructure(
            tenant_id=tenant_id,
        )

        password = admin_password or self._generate_secure_password()
        admin_username = "admin"
        admin_email = f"admin@{code}.tl"
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
        """Generate cryptographically secure password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
        return "".join(secrets.choice(alphabet) for _ in range(length))
