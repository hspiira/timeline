"""UserRole repository: user–role assignments (single entity responsibility)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateAssignmentException
from app.infrastructure.persistence.models.permission import UserRole
from app.infrastructure.persistence.models.role import Role
from app.shared.context import get_current_actor_id, get_current_actor_type
from app.shared.enums import ActorType, AuditAction
from app.shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class UserRoleRepository:
    """User–role link table only. Assign/remove and list roles for a user."""

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

    async def get_user_roles(self, user_id: str, tenant_id: str) -> list[Role]:
        now = utc_now()
        result = await self.db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Role.is_active.is_(True),
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > now),
            )
        )
        return list(result.scalars().all())

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
        try:
            self.db.add(ur)
            await self.db.flush()
            await self.db.refresh(ur)
        except IntegrityError:
            raise DuplicateAssignmentException(
                "Role already assigned to user",
                assignment_type="user_role",
                details_extra={"user_id": user_id, "role_id": role_id},
            ) from None
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

    async def remove_role_from_user(
        self, user_id: str, role_id: str, tenant_id: str
    ) -> bool:
        result = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.tenant_id == tenant_id,
            )
        )
        ur = result.scalar_one_or_none()
        if not ur:
            return False
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
