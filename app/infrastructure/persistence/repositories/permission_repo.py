"""Permission, RolePermission, UserRole repository with audit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.permission import (
    Permission,
    RolePermission,
    UserRole,
)
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.repositories.auditable_repo import AuditableRepository
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class PermissionRepository(AuditableRepository[Permission]):
    """Permission repository and role/permission, user/role assignment helpers."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Permission, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "permission"

    def _get_tenant_id(self, obj: Permission) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: Permission) -> dict[str, Any]:
        return {
            "id": obj.id,
            "code": obj.code,
            "resource": obj.resource,
            "action": obj.action,
            "description": obj.description,
        }

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> Permission | None:
        result = await self.db.execute(
            select(Permission).where(
                Permission.code == code,
                Permission.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[Permission]:
        result = await self.db.execute(
            select(Permission)
            .where(Permission.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(Permission.resource, Permission.action)
        )
        return list(result.scalars().all())

    async def get_permissions_for_role(
        self, role_id: str, tenant_id: str
    ) -> list[Permission]:
        result = await self.db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.tenant_id == tenant_id,
            )
        )
        return list(result.scalars().all())

    async def assign_permission_to_role(
        self, role_id: str, permission_id: str, tenant_id: str
    ) -> RolePermission:
        rp = RolePermission(
            tenant_id=tenant_id,
            role_id=role_id,
            permission_id=permission_id,
        )
        self.db.add(rp)
        await self.db.flush()
        await self.db.refresh(rp)
        if self._audit_enabled and self._audit_service:
            await self._audit_service.emit_audit_event(
                tenant_id=tenant_id,
                entity_type="role",
                action=AuditAction.ASSIGNED,
                entity_id=role_id,
                entity_data={"permission_id": permission_id},
                actor_id=self._get_actor_id(),
                actor_type=self._get_actor_type(),
                metadata={"permission_assigned": permission_id},
            )
        return rp

    async def remove_permission_from_role(
        self, role_id: str, permission_id: str
    ) -> bool:
        result = await self.db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        rp = result.scalar_one_or_none()
        if not rp:
            return False
        tenant_id = rp.tenant_id
        await self.db.delete(rp)
        await self.db.flush()
        if self._audit_enabled and self._audit_service:
            await self._audit_service.emit_audit_event(
                tenant_id=tenant_id,
                entity_type="role",
                action=AuditAction.UNASSIGNED,
                entity_id=role_id,
                entity_data={"permission_id": permission_id},
                actor_id=self._get_actor_id(),
                actor_type=self._get_actor_type(),
                metadata={"permission_removed": permission_id},
            )
        return True

    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        tenant_id: str,
        assigned_by: str | None = None,
    ) -> UserRole:
        ur = UserRole(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.db.add(ur)
        await self.db.flush()
        await self.db.refresh(ur)
        if self._audit_enabled and self._audit_service:
            await self._audit_service.emit_audit_event(
                tenant_id=tenant_id,
                entity_type="role",
                action=AuditAction.ASSIGNED,
                entity_id=role_id,
                entity_data={"user_id": user_id, "assigned_by": assigned_by},
                actor_id=self._get_actor_id(),
                actor_type=self._get_actor_type(),
                metadata={"role_assigned_to_user": user_id},
            )
        return ur

    async def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        result = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        ur = result.scalar_one_or_none()
        if not ur:
            return False
        tenant_id = ur.tenant_id
        await self.db.delete(ur)
        await self.db.flush()
        if self._audit_enabled and self._audit_service:
            await self._audit_service.emit_audit_event(
                tenant_id=tenant_id,
                entity_type="role",
                action=AuditAction.UNASSIGNED,
                entity_id=role_id,
                entity_data={"user_id": user_id},
                actor_id=self._get_actor_id(),
                actor_type=self._get_actor_type(),
                metadata={"role_removed_from_user": user_id},
            )
        return True

    async def get_user_roles(self, user_id: str, tenant_id: str) -> list[Role]:
        result = await self.db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Role.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
