"""System audit service: emits audit events to event store (implements IAuditService)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.application.interfaces.services import IHashService
from app.application.services.system_audit_schema import (
    SYSTEM_AUDIT_EVENT_TYPE,
    SYSTEM_AUDIT_SCHEMA_VERSION,
    SYSTEM_AUDIT_SUBJECT_REF,
    SYSTEM_AUDIT_SUBJECT_TYPE,
)
from app.infrastructure.persistence.models.event import Event
from app.infrastructure.persistence.models.subject import Subject
from app.shared.enums import ActorType, AuditAction
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class SystemAuditService:
    """Emits system audit events using tenant audit subject and schema (hash-chained)."""

    def __init__(
        self,
        db: Any,
        hash_service: IHashService,
    ) -> None:
        self.db = db
        self.hash_service = hash_service
        self._subject_cache: dict[str, str] = {}

    async def emit_audit_event(
        self,
        tenant_id: str,
        entity_type: str,
        action: Any,
        entity_id: str,
        entity_data: dict[str, Any],
        actor_id: str | None = None,
        actor_type: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event | None:
        """Emit one audit event. Returns created Event or None if audit subject missing."""
        system_subject_id = await self._get_system_subject(tenant_id)
        if not system_subject_id:
            logger.warning(
                "Audit subject not found for tenant %s. Ensure tenant initialized.",
                tenant_id,
            )
            return None

        event_time = utc_now()
        payload = self._build_audit_payload(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type or ActorType.SYSTEM,
            entity_data=entity_data,
            metadata=metadata,
            timestamp=event_time,
        )

        previous_hash = await self._get_latest_hash(system_subject_id)
        computed_hash = self.hash_service.compute_hash(
            subject_id=system_subject_id,
            event_type=SYSTEM_AUDIT_EVENT_TYPE,
            schema_version=SYSTEM_AUDIT_SCHEMA_VERSION,
            event_time=event_time,
            payload=payload,
            previous_hash=previous_hash,
        )

        event = Event(
            tenant_id=tenant_id,
            subject_id=system_subject_id,
            event_type=SYSTEM_AUDIT_EVENT_TYPE,
            schema_version=SYSTEM_AUDIT_SCHEMA_VERSION,
            event_time=event_time,
            payload=payload,
            previous_hash=previous_hash,
            hash=computed_hash,
        )
        self.db.add(event)
        logger.debug(
            "Emitted audit event for %s.%s (entity_id: %s)",
            entity_type,
            getattr(action, "value", action),
            entity_id,
        )
        return event

    async def _get_system_subject(self, tenant_id: str) -> str | None:
        if tenant_id in self._subject_cache:
            return self._subject_cache[tenant_id]
        result = await self.db.execute(
            select(Subject.id).where(
                Subject.tenant_id == tenant_id,
                Subject.subject_type == SYSTEM_AUDIT_SUBJECT_TYPE,
                Subject.external_ref == SYSTEM_AUDIT_SUBJECT_REF,
            )
        )
        subject_id = result.scalar_one_or_none()
        if subject_id:
            self._subject_cache[tenant_id] = subject_id
        return subject_id

    async def _get_latest_hash(self, subject_id: str) -> str | None:
        result = await self.db.execute(
            select(Event.hash)
            .where(Event.subject_id == subject_id)
            .order_by(Event.event_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _build_audit_payload(
        self,
        entity_type: str,
        entity_id: str,
        action: Any,
        actor_id: str | None,
        actor_type: ActorType,
        entity_data: dict[str, Any],
        metadata: dict[str, Any] | None,
        timestamp: datetime,
    ) -> dict[str, Any]:
        action_value = getattr(action, "value", str(action))
        actor_type_value = getattr(actor_type, "value", str(actor_type))
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action_value,
            "actor": {"type": actor_type_value, "id": actor_id},
            "timestamp": timestamp.isoformat(),
            "entity_data": self._sanitize_entity_data(entity_data),
            "metadata": metadata or {},
        }

    @staticmethod
    def _sanitize_entity_data(data: dict[str, Any]) -> dict[str, Any]:
        sensitive = {
            "password", "hashed_password", "secret", "api_key", "token",
            "credentials", "credentials_encrypted", "client_secret",
            "client_secret_encrypted", "refresh_token", "access_token",
        }
        out = {}
        for key, value in data.items():
            if key.lower() in sensitive:
                out[key] = "[REDACTED]"
            elif isinstance(value, datetime):
                out[key] = value.isoformat()
            elif hasattr(value, "__dict__") and not isinstance(value, dict):
                out[key] = str(value)
            else:
                out[key] = value
        return out
