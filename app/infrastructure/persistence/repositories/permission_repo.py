"""Permission repository: Permission entity only (single responsibility)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.permission import PermissionResult
from app.infrastructure.persistence.models.permission import Permission
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _permission_to_result(p: Permission) -> PermissionResult:
    """Map ORM Permission to application PermissionResult."""
    return PermissionResult(
        id=p.id,
        tenant_id=p.tenant_id,
        code=p.code,
        resource=p.resource,
        action=p.action,
        description=p.description,
    )


class PermissionRepository(AuditableRepository[Permission]):
    """Permission entity CRUD only. Role–permission and user–role are in separate repos."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: "SystemAuditService | None" = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Permission, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "permission"

    def _serialize_for_audit(self, obj: Permission) -> dict[str, Any]:
        return {
            "id": obj.id,
            "code": obj.code,
            "resource": obj.resource,
            "action": obj.action,
            "description": obj.description,
        }

    async def create_permission(
        self,
        tenant_id: str,
        code: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> PermissionResult:
        """Create a permission; return application DTO."""
        perm = Permission(
            tenant_id=tenant_id,
            code=code,
            resource=resource,
            action=action,
            description=description,
        )
        created = await self.create(perm)
        return _permission_to_result(created)

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> PermissionResult | None:
        result = await self.db.execute(
            select(Permission).where(
                Permission.code == code,
                Permission.tenant_id == tenant_id,
            )
        )
        perm = result.scalar_one_or_none()
        return _permission_to_result(perm) if perm else None

    async def get_by_id_and_tenant(
        self, permission_id: str, tenant_id: str
    ) -> Permission | None:
        """Return permission by id if it belongs to the tenant; otherwise None."""
        result = await self.db.execute(
            select(Permission).where(
                Permission.id == permission_id,
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
            .order_by(Permission.resource, Permission.action)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
