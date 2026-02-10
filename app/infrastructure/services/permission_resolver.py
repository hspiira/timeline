"""Resolves user permissions from DB (implements IPermissionResolver)."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.permission import (
    Permission,
    RolePermission,
    UserRole,
)
from app.infrastructure.persistence.models.role import Role


class PermissionResolver:
    """Resolves user permissions by querying roles and role_permissions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_permissions(
        self, user_id: str, tenant_id: str
    ) -> set[str]:
        """Return set of permission codes for user in tenant (active roles, not expired)."""
        query = (
            select(Permission.code)
            .select_from(UserRole)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Role.is_active.is_(True),
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > func.now(),
                ),
            )
        )
        result = await self.db.execute(query)
        return {row[0] for row in result.fetchall()}
