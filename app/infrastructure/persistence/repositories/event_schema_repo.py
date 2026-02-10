"""EventSchema repository with optional caching and audit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cache.cache_protocol import CacheProtocol
from app.infrastructure.cache.keys import schema_active_key
from app.infrastructure.persistence.models.event_schema import EventSchema
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class EventSchemaRepository(AuditableRepository[EventSchema]):
    """EventSchema repository. Optional cache; inject cache_ttl."""

    def __init__(
        self,
        db: AsyncSession,
        cache_service: CacheProtocol | None = None,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
        cache_ttl: int = 600,
    ) -> None:
        super().__init__(db, EventSchema, audit_service, enable_audit=enable_audit)
        self.cache = cache_service
        self.cache_ttl = cache_ttl

    def _get_entity_type(self) -> str:
        return "event_schema"

    def _get_tenant_id(self, obj: EventSchema) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: EventSchema) -> dict[str, Any]:
        return {
            "id": obj.id,
            "event_type": obj.event_type,
            "version": obj.version,
            "is_active": obj.is_active,
            "created_by": obj.created_by,
        }

    async def _on_after_create(self, obj: EventSchema) -> None:
        await super()._on_after_create(obj)
        await _invalidate_schema_cache(self.cache, obj.tenant_id, obj.event_type)

    async def _on_after_update(self, obj: EventSchema) -> None:
        await super()._on_after_update(obj)
        await _invalidate_schema_cache(self.cache, obj.tenant_id, obj.event_type)

    async def get_next_version(self, tenant_id: str, event_type: str) -> int:
        r = await self.db.execute(
            select(func.max(EventSchema.version)).where(
                and_(
                    EventSchema.tenant_id == tenant_id,
                    EventSchema.event_type == event_type,
                )
            )
        )
        return (r.scalar() or 0) + 1

    async def create_schema(
        self,
        tenant_id: str,
        event_type: str,
        schema_definition: dict[str, Any],
        is_active: bool = False,
        created_by: str | None = None,
    ) -> EventSchema:
        """Create event schema with next version; return created entity."""
        version = await self.get_next_version(tenant_id, event_type)
        schema = EventSchema(
            tenant_id=tenant_id,
            event_type=event_type,
            schema_definition=schema_definition,
            version=version,
            is_active=is_active,
            created_by=created_by,
        )
        return await self.create(schema)

    async def get_active_schema(
        self, tenant_id: str, event_type: str
    ) -> EventSchema | None:
        if self.cache and self.cache.is_available():
            cached = await self.cache.get(schema_active_key(tenant_id, event_type))
            if cached is not None:
                schema = EventSchema(**cached)
                self.db.add(schema)
                return schema
        result = await self.db.execute(
            select(EventSchema)
            .where(
                and_(
                    EventSchema.tenant_id == tenant_id,
                    EventSchema.event_type == event_type,
                    EventSchema.is_active.is_(True),
                )
            )
            .order_by(EventSchema.version.desc())
            .limit(1)
        )
        schema = result.scalar_one_or_none()
        if schema and self.cache and self.cache.is_available():
            d = {
                "id": schema.id,
                "tenant_id": schema.tenant_id,
                "event_type": schema.event_type,
                "version": schema.version,
                "schema_definition": schema.schema_definition,
                "is_active": schema.is_active,
                "created_at": (
                    schema.created_at.isoformat() if schema.created_at else None
                ),
                "updated_at": (
                    schema.updated_at.isoformat() if schema.updated_at else None
                ),
            }
            await self.cache.set(
                schema_active_key(tenant_id, event_type), d, ttl=self.cache_ttl
            )
        return schema

    async def get_by_version(
        self, tenant_id: str, event_type: str, version: int
    ) -> EventSchema | None:
        result = await self.db.execute(
            select(EventSchema).where(
                and_(
                    EventSchema.tenant_id == tenant_id,
                    EventSchema.event_type == event_type,
                    EventSchema.version == version,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> list[EventSchema]:
        result = await self.db.execute(
            select(EventSchema)
            .where(
                and_(
                    EventSchema.tenant_id == tenant_id,
                    EventSchema.event_type == event_type,
                )
            )
            .order_by(EventSchema.version.desc())
        )
        return list(result.scalars().all())

    async def deactivate_schema(self, schema_id: str) -> EventSchema | None:
        schema = await self.get_by_id(schema_id)
        if not schema:
            return None
        schema.is_active = False
        updated = await self.update(schema)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return updated

    async def activate_schema(self, schema_id: str) -> EventSchema | None:
        schema = await self.get_by_id(schema_id)
        if not schema:
            return None
        schema.is_active = True
        updated = await self.update(schema)
        await self.emit_custom_audit(updated, AuditAction.ACTIVATED)
        return updated


async def _invalidate_schema_cache(
    cache: CacheProtocol | None, tenant_id: str, event_type: str
) -> None:
    if cache and cache.is_available():
        await cache.delete(schema_active_key(tenant_id, event_type))
