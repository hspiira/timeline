"""Tenant repository with optional caching and audit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TenantStatus
from app.domain.exceptions import TenantAlreadyExistsError
from app.infrastructure.cache.cache_protocol import CacheProtocol
from app.infrastructure.cache.keys import tenant_code_key, tenant_key
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class TenantRepository(AuditableRepository[Tenant]):
    """Tenant repository. Optional cache (inject cache_ttl). Uses tenant_key/tenant_code_key."""

    def __init__(
        self,
        db: AsyncSession,
        cache_service: CacheProtocol | None = None,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
        cache_ttl: int = 900,
    ) -> None:
        super().__init__(db, Tenant, audit_service, enable_audit=enable_audit)
        self.cache = cache_service
        self.cache_ttl = cache_ttl

    def _get_entity_type(self) -> str:
        return "tenant"

    def _get_tenant_id(self, obj: Tenant) -> str:
        return obj.id

    def _serialize_for_audit(self, obj: Tenant) -> dict[str, Any]:
        return {"id": obj.id, "code": obj.code, "name": obj.name, "status": obj.status}

    async def get_by_id(self, tenant_id: str) -> Tenant | None:
        """Get tenant by ID, from cache if available."""
        if self.cache and self.cache.is_available():
            cached = await self.cache.get(tenant_key(tenant_id))
            if cached is not None:
                tenant = Tenant(**cached)
                self.db.add(tenant)
                return tenant
        tenant = await super().get_by_id(tenant_id)
        if tenant and self.cache and self.cache.is_available():
            d = _tenant_to_dict(tenant)
            await self.cache.set(tenant_key(tenant_id), d, ttl=self.cache_ttl)
        return tenant

    async def create_tenant(self, code: str, name: str, status: str) -> Tenant:
        """Create tenant from code/name/status; return created entity.

        Raises TenantAlreadyExistsError on unique constraint violation (e.g. duplicate code).
        """
        tenant = Tenant(code=code, name=name, status=status)
        try:
            return await self.create(tenant)
        except IntegrityError:
            raise TenantAlreadyExistsError(code)

    async def get_by_code(self, code: str) -> Tenant | None:
        """Get tenant by unique code, from cache if available."""
        if self.cache and self.cache.is_available():
            cached = await self.cache.get(tenant_code_key(code))
            if cached is not None:
                tenant = Tenant(**cached)
                self.db.add(tenant)
                return tenant
        result = await self.db.execute(select(Tenant).where(Tenant.code == code))
        tenant = result.scalar_one_or_none()
        if tenant and self.cache and self.cache.is_available():
            d = _tenant_to_dict(tenant)
            await self.cache.set(tenant_code_key(code), d, ttl=self.cache_ttl)
            await self.cache.set(tenant_key(tenant.id), d, ttl=self.cache_ttl)
        return tenant

    async def get_active_tenants(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """Get active tenants with pagination."""
        result = await self.db.execute(
            select(Tenant)
            .where(Tenant.status == TenantStatus.ACTIVE.value)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self, tenant_id: str, status: TenantStatus
    ) -> Tenant | None:
        """Update tenant status and emit status_changed audit."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None
        old_status = tenant.status
        tenant.status = status.value
        updated = await self.update(tenant)
        await self.emit_custom_audit(
            updated,
            AuditAction.STATUS_CHANGED,
            metadata={"old_status": old_status, "new_status": status.value},
        )
        return updated

    async def _on_after_create(self, obj: Tenant) -> None:
        await super()._on_after_create(obj)
        await _invalidate_tenant_cache(self.cache, obj.id, obj.code)

    async def _on_after_update(self, obj: Tenant) -> None:
        await super()._on_after_update(obj)
        await _invalidate_tenant_cache(self.cache, obj.id, obj.code)

    async def _on_before_delete(self, obj: Tenant) -> None:
        await super()._on_before_delete(obj)
        await _invalidate_tenant_cache(self.cache, obj.id, obj.code)


def _tenant_to_dict(tenant: Tenant) -> dict[str, Any]:
    return {
        "id": tenant.id,
        "code": tenant.code,
        "name": tenant.name,
        "status": tenant.status,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }


async def _invalidate_tenant_cache(
    cache: CacheProtocol | None, tenant_id: str, tenant_code: str
) -> None:
    if cache and cache.is_available():
        await cache.delete(tenant_key(tenant_id))
        await cache.delete(tenant_code_key(tenant_code))
