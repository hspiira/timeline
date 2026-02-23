"""EventSchema repository with optional caching and audit. Returns application DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event_schema import EventSchemaResult
from app.domain.value_objects.core import EventType
from app.infrastructure.cache.cache_protocol import CacheProtocol
from app.infrastructure.cache.keys import schema_active_key
from app.infrastructure.persistence.models.event_schema import EventSchema
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _event_schema_to_result(s: EventSchema) -> EventSchemaResult:
    """Map ORM EventSchema to application EventSchemaResult."""
    return EventSchemaResult(
        id=s.id,
        tenant_id=s.tenant_id,
        event_type=EventType(s.event_type),
        schema_definition=s.schema_definition,
        version=s.version,
        is_active=s.is_active,
        allowed_subject_types=s.allowed_subject_types,
        created_by=s.created_by,
    )


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

    async def get_entity_by_id(self, schema_id: str) -> EventSchema | None:
        """Get schema ORM by id for update/delete."""
        return await super().get_by_id(schema_id)

    async def get_by_id_and_tenant(
        self, schema_id: str, tenant_id: str
    ) -> EventSchemaResult | None:
        """Return schema by ID and tenant (tenant-scoped; safe when RLS is off)."""
        result = await self.db.execute(
            select(EventSchema).where(
                EventSchema.id == schema_id,
                EventSchema.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _event_schema_to_result(row) if row else None

    async def get_entity_by_id_and_tenant(
        self, schema_id: str, tenant_id: str
    ) -> EventSchema | None:
        """Get schema ORM by id and tenant for update/delete (tenant-scoped)."""
        result = await self.db.execute(
            select(EventSchema).where(
                EventSchema.id == schema_id,
                EventSchema.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, schema_id: str) -> EventSchemaResult | None:
        result = await self.db.execute(select(EventSchema).where(EventSchema.id == schema_id))
        row = result.scalar_one_or_none()
        return _event_schema_to_result(row) if row else None

    async def create_schema(
        self,
        tenant_id: str,
        event_type: str,
        schema_definition: dict[str, Any],
        is_active: bool = True,
        allowed_subject_types: list[str] | None = None,
        created_by: str | None = None,
    ) -> EventSchemaResult:
        """Create event schema with next version; return created entity.

        Retries on IntegrityError (e.g. concurrent insert for same version).
        """
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                async with self.db.begin_nested():
                    version = await self.get_next_version(tenant_id, event_type)
                    schema = EventSchema(
                        tenant_id=tenant_id,
                        event_type=event_type,
                        schema_definition=schema_definition,
                        version=version,
                        is_active=is_active,
                        allowed_subject_types=allowed_subject_types,
                        created_by=created_by,
                    )
                    created = await self.create(schema)
                    if is_active:
                        # Deactivate any other active schema for this (tenant_id, event_type)
                        other = await self.db.execute(
                            select(EventSchema).where(
                                and_(
                                    EventSchema.tenant_id == tenant_id,
                                    EventSchema.event_type == event_type,
                                    EventSchema.is_active.is_(True),
                                    EventSchema.id != created.id,
                                )
                            )
                        )
                        for other_schema in other.scalars().all():
                            other_schema.is_active = False
                            await self.update(other_schema)
                            await self.emit_custom_audit(other_schema, AuditAction.DEACTIVATED)
                        await _invalidate_schema_cache(
                            self.cache, tenant_id, event_type
                        )
                    return _event_schema_to_result(created)
            except IntegrityError:
                if attempt == max_attempts - 1:
                    raise
                # Savepoint rolled back; retry with fresh version on next iteration
        raise RuntimeError("create_schema exhausted retries")  # unreachable

    async def get_active_schema(
        self, tenant_id: str, event_type: str
    ) -> EventSchemaResult | None:
        if self.cache and self.cache.is_available():
            cached = await self.cache.get(schema_active_key(tenant_id, event_type))
            if cached is not None:
                # Parse ISO datetime strings so the model receives datetime objects
                cached = dict(cached)
                cached.setdefault("created_by", None)
                cached.setdefault("allowed_subject_types", None)
                for key in ("created_at", "updated_at"):
                    if cached.get(key) and isinstance(cached[key], str):
                        cached[key] = datetime.fromisoformat(cached[key])
                schema = EventSchema(**cached)
                merged = await self.db.merge(schema)
                return _event_schema_to_result(merged)
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
            # Store datetimes as ISO strings; cache read path parses with datetime.fromisoformat()
            d = {
                "id": schema.id,
                "tenant_id": schema.tenant_id,
                "event_type": schema.event_type,
                "version": schema.version,
                "schema_definition": schema.schema_definition,
                "is_active": schema.is_active,
                "allowed_subject_types": schema.allowed_subject_types,
                "created_by": schema.created_by,
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
        return _event_schema_to_result(schema) if schema else None

    async def get_by_version(
        self, tenant_id: str, event_type: str, version: int
    ) -> EventSchemaResult | None:
        result = await self.db.execute(
            select(EventSchema).where(
                and_(
                    EventSchema.tenant_id == tenant_id,
                    EventSchema.event_type == event_type,
                    EventSchema.version == version,
                )
            )
        )
        row = result.scalar_one_or_none()
        return _event_schema_to_result(row) if row else None

    async def get_all_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> list[EventSchemaResult]:
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
        return [_event_schema_to_result(s) for s in result.scalars().all()]

    async def get_all_for_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventSchemaResult]:
        """Return all event schemas for the tenant (any event type), ordered by event_type and version desc."""
        result = await self.db.execute(
            select(EventSchema)
            .where(EventSchema.tenant_id == tenant_id)
            .order_by(EventSchema.event_type.asc(), EventSchema.version.desc())
            .offset(skip)
            .limit(limit)
        )
        return [_event_schema_to_result(s) for s in result.scalars().all()]

    async def deactivate_schema(self, schema_id: str) -> EventSchema | None:
        schema = await super().get_by_id(schema_id)
        if not schema:
            return None
        schema.is_active = False
        updated = await self.update(schema)
        await self.emit_custom_audit(updated, AuditAction.DEACTIVATED)
        return updated

    async def activate_schema(self, schema_id: str) -> EventSchema | None:
        schema = await super().get_by_id(schema_id)
        if not schema:
            return None
        # Deactivate any currently active schema for the same (tenant_id, event_type)
        result = await self.db.execute(
            select(EventSchema).where(
                and_(
                    EventSchema.tenant_id == schema.tenant_id,
                    EventSchema.event_type == schema.event_type,
                    EventSchema.is_active.is_(True),
                    EventSchema.id != schema.id,
                )
            )
        )
        current_active = result.scalar_one_or_none()
        if current_active:
            current_active.is_active = False
            await self.update(current_active)
            await self.emit_custom_audit(current_active, AuditAction.DEACTIVATED)
        schema.is_active = True
        updated = await self.update(schema)
        await self.emit_custom_audit(updated, AuditAction.ACTIVATED)
        return updated


async def _invalidate_schema_cache(
    cache: CacheProtocol | None, tenant_id: str, event_type: str
) -> None:
    if cache and cache.is_available():
        await cache.delete(schema_active_key(tenant_id, event_type))
