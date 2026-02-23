"""Auditable repository: automatic audit event emission on CRUD.

Extends BaseRepository; subclasses implement _get_entity_type, _get_tenant_id,
_serialize_for_audit. Audit service is injected (no lazy init). When
audit_service is None, no events are emitted.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.domain.exceptions import ValidationException
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.shared.context import get_current_actor_id, get_current_actor_type
from app.shared.enums import ActorType, AuditAction
from app.shared.telemetry.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.infrastructure.services.system_audit_service import SystemAuditService

ModelType = TypeVar("ModelType", bound=Base)
_logger = get_logger(__name__)


class AuditableRepository(BaseRepository[ModelType]):
    """Repository that emits audit events on create/update/delete.

    Pass audit_service in constructor when auditing is needed (DIP).
    Subclasses implement _get_entity_type, _get_tenant_id, _serialize_for_audit.
    """

    def __init__(
        self,
        db: AsyncSession,
        model: type[ModelType],
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, model)
        self._audit_service = audit_service
        self._audit_enabled = enable_audit

    def enable_auditing(self, audit_service: SystemAuditService | None = None) -> None:
        """Turn on auditing and optionally set the service."""
        self._audit_enabled = True
        if audit_service is not None:
            self._audit_service = audit_service

    def disable_auditing(self) -> None:
        """Turn off auditing."""
        self._audit_enabled = False

    @property
    def audit_service(self) -> "SystemAuditService | None":
        """Injected audit service (read-only)."""
        return self._audit_service

    @abstractmethod
    def _get_entity_type(self) -> str:
        """Return entity type for audit (e.g. 'subject')."""
        ...

    def _get_tenant_id(self, obj: ModelType) -> str:
        """Return tenant_id from the entity (default: obj.tenant_id or obj.id for Tenant)."""
        return getattr(obj, "tenant_id", None) or getattr(obj, "id", "")

    @abstractmethod
    def _serialize_for_audit(self, obj: ModelType) -> dict[str, Any]:
        """Return dict representation for audit payload."""
        ...

    def _get_actor_id(self) -> str | None:
        """Current actor ID from request context."""
        return get_current_actor_id()

    def _get_actor_type(self) -> ActorType:
        """Current actor type from request context."""
        return get_current_actor_type()

    def _should_audit(self, action: AuditAction, obj: ModelType) -> bool:
        """Override to skip auditing for certain operations."""
        return True

    async def _emit_audit_event(
        self,
        action: AuditAction,
        obj: ModelType,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit one audit event. No-op if auditing disabled or service not set."""
        if not self._audit_enabled or not self._should_audit(action, obj):
            return
        if self._audit_service is None:
            return
        try:
            await self._audit_service.emit_audit_event(
                tenant_id=self._get_tenant_id(obj),
                entity_type=self._get_entity_type(),
                action=action,
                entity_id=getattr(obj, "id", str(obj)),
                entity_data=self._serialize_for_audit(obj),
                actor_id=self._get_actor_id(),
                actor_type=self._get_actor_type(),
                metadata=metadata,
            )
        except Exception as e:
            _logger.warning(
                "Failed to emit audit event for %s.%s: %s",
                self._get_entity_type(),
                action.value,
                str(e),
                exc_info=True,
            )

    async def _on_after_create(self, obj: ModelType) -> None:
        await super()._on_after_create(obj)
        await self._emit_audit_event(AuditAction.CREATED, obj)

    async def _on_after_update(self, obj: ModelType) -> None:
        await super()._on_after_update(obj)
        await self._emit_audit_event(AuditAction.UPDATED, obj)

    async def _on_before_delete(self, obj: ModelType) -> None:
        await super()._on_before_delete(obj)
        await self._emit_audit_event(AuditAction.DELETED, obj)

    async def update_without_audit(self, obj: ModelType) -> ModelType:
        """Persist update without emitting UPDATED audit (e.g. before emit_custom_audit)."""
        if object_session(obj) is None:
            obj = await self.db.merge(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def emit_custom_audit(
        self,
        obj: ModelType,
        action: AuditAction,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit a custom audit event (e.g. activated, deactivated)."""
        await self._emit_audit_event(action, obj, metadata)


class TenantScopedRepository(AuditableRepository[ModelType]):
    """Repository that enforces tenant isolation.

    All reads (get_by_id, get_all) and writes (create, update, delete) are
    scoped to a single tenant_id. Pass tenant_id at construction; the repo
    then auto-adds tenant filtering and rejects cross-tenant writes.
    """

    def __init__(
        self,
        db: "AsyncSession",
        model: type[ModelType],
        tenant_id: str,
        audit_service: "SystemAuditService | None" = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, model, audit_service, enable_audit=enable_audit)
        self._tenant_id = tenant_id

    def _assert_tenant(self, obj: ModelType, operation: str) -> None:
        """Raise if obj.tenant_id does not match this repo's tenant."""
        if getattr(obj, "tenant_id", None) != self._tenant_id:
            raise ValidationException(
                f"Cannot {operation} entity belonging to another tenant",
                field="tenant_id",
            )

    async def get_by_id(self, entity_id: str) -> ModelType | None:
        """Return a single record by primary key and tenant_id, or None."""
        model: Any = self.model
        result = await self.db.execute(
            select(self.model).where(
                model.id == entity_id,
                model.tenant_id == self._tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Return records for this tenant with pagination."""
        model: Any = self.model
        result = await self.db.execute(
            select(self.model)
            .where(model.tenant_id == self._tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """Persist and run hooks; ensure obj.tenant_id matches this repo."""
        self._assert_tenant(obj, "create")
        return await super().create(obj)

    async def update(
        self, obj: ModelType, *, skip_existence_check: bool = False
    ) -> ModelType:
        """Update only if obj belongs to this tenant."""
        self._assert_tenant(obj, "update")
        return await super().update(obj, skip_existence_check=skip_existence_check)

    async def delete(self, obj: ModelType) -> None:
        """Delete only if obj belongs to this tenant."""
        self._assert_tenant(obj, "delete")
        await super().delete(obj)
