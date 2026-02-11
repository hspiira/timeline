"""Role repository with audit. Read methods return RoleResult (DTO); entity getters return ORM for writes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.role import RoleResult
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _role_to_result(r: Role) -> RoleResult:
    """Map ORM Role to application RoleResult."""
    return RoleResult(
        id=r.id,
        tenant_id=r.tenant_id,
        code=r.code,
        name=r.name,
        description=r.description,
        is_system=r.is_system,
        is_active=r.is_active,
    )


class RoleRepository(AuditableRepository[Role]):
    """Role repository. Read methods return RoleResult; use get_entity_by_id_and_tenant for update/delete."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Role, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "role"

    def _serialize_for_audit(self, obj: Role) -> dict[str, Any]:
        return {
            "id": obj.id,
            "code": obj.code,
            "name": obj.name,
            "description": obj.description,
            "is_system": obj.is_system,
            "is_active": obj.is_active,
        }

    async def create_role(
        self,
        tenant_id: str,
        code: str,
        name: str,
        description: str | None = None,
        *,
        is_system: bool = False,
        is_active: bool = True,
    ) -> RoleResult:
        """Create a role; return read-model DTO."""
        role = Role(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description,
            is_system=is_system,
            is_active=is_active,
        )
        created = await self.create(role)
        return _role_to_result(created)

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> RoleResult | None:
        result = await self.db.execute(
            select(Role).where(Role.code == code, Role.tenant_id == tenant_id)
        )
        row = result.scalar_one_or_none()
        return _role_to_result(row) if row else None

    async def get_by_id_and_tenant(
        self, role_id: str, tenant_id: str
    ) -> RoleResult | None:
        """Return role by id and tenant (read-model DTO)."""
        orm = await self.get_entity_by_id_and_tenant(role_id, tenant_id)
        return _role_to_result(orm) if orm else None

    async def get_entity_by_id_and_tenant(
        self, role_id: str, tenant_id: str
    ) -> Role | None:
        """Return role ORM by id and tenant for update/delete."""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        *,
        include_inactive: bool = False,
    ) -> list[RoleResult]:
        q = select(Role).where(Role.tenant_id == tenant_id)
        if not include_inactive:
            q = q.where(Role.is_active.is_(True))
        q = q.offset(skip).limit(limit).order_by(Role.created_at.desc())
        result = await self.db.execute(q)
        return [_role_to_result(r) for r in result.scalars().all()]

    async def deactivate(self, role_id: str, tenant_id: str) -> RoleResult | None:
        """Deactivate role; returns updated DTO or None if not found / system role."""
        role = await self.get_entity_by_id_and_tenant(role_id, tenant_id)
        if not role or role.is_system:
            return None
        role.is_active = False
        updated = await self.update(role)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return _role_to_result(updated)

    async def activate(self, role_id: str, tenant_id: str) -> RoleResult | None:
        """Activate role; returns updated DTO or None if not found / system role."""
        role = await self.get_entity_by_id_and_tenant(role_id, tenant_id)
        if not role or role.is_system:
            return None
        role.is_active = True
        updated = await self.update(role)
        await self.emit_custom_audit(updated, AuditAction.ACTIVATED)
        return _role_to_result(updated)

    async def get_system_roles(self, tenant_id: str) -> list[RoleResult]:
        result = await self.db.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.is_system.is_(True),
                Role.is_active.is_(True),
            )
        )
        return [_role_to_result(r) for r in result.scalars().all()]
