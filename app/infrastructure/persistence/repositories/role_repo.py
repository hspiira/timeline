"""Role repository with audit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.repositories.auditable_repo import AuditableRepository
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.application.services.system_audit_service import SystemAuditService


class RoleRepository(AuditableRepository[Role]):
    """Role repository."""

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

    def _get_tenant_id(self, obj: Role) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: Role) -> dict[str, Any]:
        return {
            "id": obj.id,
            "code": obj.code,
            "name": obj.name,
            "description": obj.description,
            "is_system": obj.is_system,
            "is_active": obj.is_active,
        }

    async def get_by_code_and_tenant(self, code: str, tenant_id: str) -> Role | None:
        result = await self.db.execute(
            select(Role).where(Role.code == code, Role.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Role]:
        q = select(Role).where(Role.tenant_id == tenant_id)
        if not include_inactive:
            q = q.where(Role.is_active.is_(True))
        q = q.offset(skip).limit(limit).order_by(Role.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def deactivate(self, role_id: str) -> Role | None:
        role = await self.get_by_id(role_id)
        if not role:
            return None
        role.is_active = False
        updated = await self.update(role)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return updated

    async def activate(self, role_id: str) -> Role | None:
        role = await self.get_by_id(role_id)
        if not role:
            return None
        role.is_active = True
        updated = await self.update(role)
        await self.emit_custom_audit(updated, AuditAction.ACTIVATED)
        return updated

    async def get_system_roles(self, tenant_id: str) -> list[Role]:
        result = await self.db.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.is_system.is_(True),
                Role.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
