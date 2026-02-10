"""Event creation use case: single and bulk with hash chaining and optional schema validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import jsonschema

from app.application.dtos.event import EventToPersist
from app.application.interfaces.repositories import (
    IEventRepository,
    IEventSchemaRepository,
    ISubjectRepository,
)
from app.application.interfaces.services import IHashService
from app.shared.telemetry.logging import get_logger

if TYPE_CHECKING:
    from app.application.interfaces.services import IWorkflowEngine
    from app.infrastructure.persistence.models.event import Event
    from app.schemas.event import EventCreate

logger = get_logger(__name__)


class EventService:
    """Creates events with hash chaining and optional schema validation (IEventService)."""

    def __init__(
        self,
        event_repo: IEventRepository,
        hash_service: IHashService,
        subject_repo: ISubjectRepository,
        schema_repo: IEventSchemaRepository | None = None,
        workflow_engine: "IWorkflowEngine | None" = None,
    ) -> None:
        self.event_repo = event_repo
        self.hash_service = hash_service
        self.subject_repo = subject_repo
        self.schema_repo = schema_repo
        self.workflow_engine = workflow_engine

    async def create_event(
        self,
        tenant_id: str,
        event: "EventCreate",
        *,
        trigger_workflows: bool = True,
    ) -> "Event":
        """Create one event; validate subject and schema, compute hash, optionally trigger workflows."""
        subject = await self.subject_repo.get_by_id_and_tenant(
            event.subject_id, tenant_id
        )
        if not subject:
            raise ValueError(
                f"Subject '{event.subject_id}' not found or does not belong to tenant"
            )

        if self.schema_repo:
            await self._validate_payload(
                tenant_id,
                event.event_type,
                event.schema_version,
                event.payload,
            )

        prev_event = await self.event_repo.get_last_event(event.subject_id, tenant_id)
        prev_hash = prev_event.hash if prev_event else None

        if prev_event and event.event_time <= prev_event.event_time:
            raise ValueError(
                f"Event time must be after previous event time {prev_event.event_time}"
            )

        event_hash = self.hash_service.compute_hash(
            subject_id=event.subject_id,
            event_type=event.event_type,
            schema_version=event.schema_version,
            event_time=event.event_time,
            payload=event.payload,
            previous_hash=prev_hash,
        )

        created = await self.event_repo.create_event(
            tenant_id, event, event_hash, prev_hash
        )

        if trigger_workflows and self.workflow_engine:
            await self._trigger_workflows(created, tenant_id)

        return created

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list["EventCreate"],
        *,
        skip_schema_validation: bool = False,
        trigger_workflows: bool = False,
    ) -> list["Event"]:
        """Bulk create events (e.g. email sync). Hashes computed sequentially; single DB roundtrip."""
        if not events:
            return []

        subject_ids = {e.subject_id for e in events}
        for subject_id in subject_ids:
            subject = await self.subject_repo.get_by_id_and_tenant(
                subject_id, tenant_id
            )
            if not subject:
                raise ValueError(
                    f"Subject '{subject_id}' not found or does not belong to tenant"
                )

        first_subject_id = events[0].subject_id
        prev_event = await self.event_repo.get_last_event(first_subject_id, tenant_id)
        prev_hash = prev_event.hash if prev_event else None
        prev_time = prev_event.event_time if prev_event else None

        to_persist: list[EventToPersist] = []
        for event_data in events:
            if prev_time and event_data.event_time <= prev_time:
                raise ValueError(
                    "Event time must be after previous; events must be sorted by event_time"
                )
            if not skip_schema_validation and self.schema_repo:
                await self._validate_payload(
                    tenant_id,
                    event_data.event_type,
                    event_data.schema_version,
                    event_data.payload,
                )
            event_hash = self.hash_service.compute_hash(
                subject_id=event_data.subject_id,
                event_type=event_data.event_type,
                schema_version=event_data.schema_version,
                event_time=event_data.event_time,
                payload=event_data.payload,
                previous_hash=prev_hash,
            )
            to_persist.append(
                EventToPersist(
                    subject_id=event_data.subject_id,
                    event_type=event_data.event_type,
                    schema_version=event_data.schema_version,
                    event_time=event_data.event_time,
                    payload=event_data.payload,
                    hash=event_hash,
                    previous_hash=prev_hash,
                )
            )
            prev_hash = event_hash
            prev_time = event_data.event_time

        created = await self.event_repo.create_events_bulk(tenant_id, to_persist)

        if trigger_workflows and self.workflow_engine:
            for ev in created:
                await self._trigger_workflows(ev, tenant_id)

        return created

    async def _trigger_workflows(self, event: "Event", tenant_id: str) -> list[Any]:
        if not self.workflow_engine:
            return []
        try:
            result = await self.workflow_engine.process_event_triggers(event, tenant_id)
            return result or []
        except Exception:
            logger.exception(
                "Workflow trigger failed for event %s (type: %s)",
                event.id,
                event.event_type,
            )
            return []

    async def _validate_payload(
        self,
        tenant_id: str,
        event_type: str,
        schema_version: int,
        payload: dict[str, Any],
    ) -> None:
        if not self.schema_repo:
            raise ValueError("Schema repository not configured")
        schema = await self.schema_repo.get_by_version(
            tenant_id, event_type, schema_version
        )
        if not schema:
            raise ValueError(
                f"Schema version {schema_version} not found for event type '{event_type}'"
            )
        if not schema.is_active:
            raise ValueError(
                f"Schema version {schema_version} for '{event_type}' is not active"
            )
        try:
            jsonschema.validate(instance=payload, schema=schema.schema_definition)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Payload validation failed against schema v{schema_version}: {e.message}"
            ) from e
        except jsonschema.SchemaError as e:
            raise ValueError(
                f"Invalid schema definition for v{schema_version}: {e.message}"
            ) from e
