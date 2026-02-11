"""RolePermission repository: role–permission assignments (single entity responsibility)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateAssignmentException
from app.infrastructure.persistence.models.permission import (
    Permission,
    RolePermission,
)
from app.shared.context import get_current_actor_id, get_current_actor_type
from app.shared.enums import ActorType, AuditAction
from app.shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class RolePermissionRepository:
    """Role–permission link table only. Assign/remove and query permissions for a role."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: "SystemAuditService | None" = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        self.db = db
        self._audit_service = audit_service
        self._audit_enabled = enable_audit

    def _get_actor_id(self) -> str | None:
        return get_current_actor_id()

    def _get_actor_type(self) -> ActorType:
        return get_current_actor_type()

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
        try:
            self.db.add(rp)
            await self.db.flush()
            await self.db.refresh(rp)
        except IntegrityError:
            raise DuplicateAssignmentException(
                "Permission already assigned to role",
                assignment_type="role_permission",
                details_extra={"role_id": role_id, "permission_id": permission_id},
            ) from None
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
        self, role_id: str, permission_id: str, tenant_id: str
    ) -> bool:
        result = await self.db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
                RolePermission.tenant_id == tenant_id,
            )
        )
        rp = result.scalar_one_or_none()
        if not rp:
            return False
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
