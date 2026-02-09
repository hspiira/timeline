"""System audit service: emits audit events for CRUD (stub until Phase 5)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class SystemAuditService:
    """Emits audit events to the event store. Full implementation in Phase 5."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def emit_audit_event(
        self,
        tenant_id: str,
        entity_type: str,
        action: Any,
        entity_id: str,
        entity_data: dict[str, Any],
        actor_id: str | None,
        actor_type: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit one audit event. Stub: no-op until Phase 5."""
        pass
