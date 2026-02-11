"""Event creation use case: single and bulk with hash chaining and optional schema validation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from app.application.dtos.event import CreateEventCommand, EventResult, EventToPersist
from app.application.interfaces.repositories import (
    IEventRepository,
    ISubjectRepository,
)
from app.application.interfaces.services import IHashService
from app.domain.entities.event import EventEntity
from app.domain.exceptions import ResourceNotFoundException
from app.domain.value_objects.core import EventChain, EventType, Hash
from app.shared.telemetry.logging import get_logger

if TYPE_CHECKING:
    from app.application.interfaces.services import IEventSchemaValidator, IWorkflowEngine


def _event_result_to_entity(r: EventResult) -> EventEntity:
    """Map EventResult (application DTO) to EventEntity (domain entity)."""
    current_hash = Hash(r.hash)
    previous_hash = Hash(r.previous_hash) if r.previous_hash else None
    chain = EventChain(current_hash=current_hash, previous_hash=previous_hash)
    return EventEntity(
        id=r.id,
        tenant_id=r.tenant_id,
        subject_id=r.subject_id,
        event_type=EventType(r.event_type),
        event_time=r.event_time,
        payload=r.payload,
        chain=chain,
    )

logger = get_logger(__name__)


class EventService:
    """Creates events with hash chaining and optional schema validation (IEventService)."""

    def __init__(
        self,
        event_repo: IEventRepository,
        hash_service: IHashService,
        subject_repo: ISubjectRepository,
        schema_validator: "IEventSchemaValidator | None" = None,
        workflow_engine_provider: Callable[[], "IWorkflowEngine | None"] | None = None,
    ) -> None:
        self.event_repo = event_repo
        self.hash_service = hash_service
        self.subject_repo = subject_repo
        self.schema_validator = schema_validator
        self._workflow_engine_provider = workflow_engine_provider

    @property
    def workflow_engine(self) -> "IWorkflowEngine | None":
        """Resolve workflow engine lazily to avoid circular init."""
        if self._workflow_engine_provider is None:
            return None
        return self._workflow_engine_provider()

    async def create_event(
        self,
        tenant_id: str,
        data: CreateEventCommand,
        *,
        trigger_workflows: bool = True,
    ) -> EventEntity:
        """Create one event; validate subject and schema, compute hash, optionally trigger workflows."""
        subject = await self.subject_repo.get_by_id_and_tenant(
            data.subject_id, tenant_id
        )
        if not subject:
            raise ResourceNotFoundException("subject", data.subject_id)

        if self.schema_validator:
            await self.schema_validator.validate_payload(
                tenant_id,
                data.event_type,
                data.schema_version,
                data.payload,
            )

        prev_event = await self.event_repo.get_last_event(data.subject_id, tenant_id)
        prev_hash = prev_event.hash if prev_event else None

        EventEntity.validate_event_time_after_previous(
            data.event_time,
            prev_event.event_time if prev_event else None,
        )

        event_hash = self.hash_service.compute_hash(
            subject_id=data.subject_id,
            event_type=data.event_type,
            schema_version=data.schema_version,
            event_time=data.event_time,
            payload=data.payload,
            previous_hash=prev_hash,
        )

        created = await self.event_repo.create_event(
            tenant_id, data, event_hash, prev_hash
        )

        entity = _event_result_to_entity(created)
        if trigger_workflows and self.workflow_engine:
            await self._trigger_workflows(entity, tenant_id)

        return entity

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list[CreateEventCommand],
        *,
        skip_schema_validation: bool = False,
        trigger_workflows: bool = False,
    ) -> list[EventEntity]:
        """Bulk create events (e.g. email sync). Hashes computed sequentially; single DB roundtrip."""
        if not events:
            return []

        subject_ids = {e.subject_id for e in events}
        for subject_id in subject_ids:
            subject = await self.subject_repo.get_by_id_and_tenant(
                subject_id, tenant_id
            )
            if not subject:
                raise ResourceNotFoundException("subject", subject_id)

        # Fetch last event per subject so each subject has an independent hash chain.
        chain_state: dict[str, tuple[str | None, datetime | None]] = {}
        for sid in subject_ids:
            prev_ev = await self.event_repo.get_last_event(sid, tenant_id)
            chain_state[sid] = (
                prev_ev.hash if prev_ev else None,
                prev_ev.event_time if prev_ev else None,
            )

        to_persist: list[EventToPersist] = []
        for event_data in events:
            prev_hash, prev_time = chain_state[event_data.subject_id]
            EventEntity.validate_event_time_after_previous(
                event_data.event_time,
                prev_time,
            )
            if not skip_schema_validation and self.schema_validator:
                await self.schema_validator.validate_payload(
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
            chain_state[event_data.subject_id] = (event_hash, event_data.event_time)

        created = await self.event_repo.create_events_bulk(tenant_id, to_persist)
        entities = [_event_result_to_entity(ev) for ev in created]

        if trigger_workflows and self.workflow_engine:
            for ev in entities:
                await self._trigger_workflows(ev, tenant_id)

        return entities

    async def _trigger_workflows(
        self, event: EventEntity, tenant_id: str
    ) -> list[Any]:
        if not self.workflow_engine:
            return []
        try:
            result = await self.workflow_engine.process_event_triggers(event, tenant_id)
            return result or []
        except (AssertionError, AttributeError, IndexError, KeyError, NameError, TypeError):
            # Programming errors: do not mask; re-raise so they surface in tests and logs.
            raise
        except Exception:
            # Runtime/infra failures (e.g. network, DB in workflow): log and do not fail event creation.
            logger.exception(
                "Workflow trigger failed for event %s (type: %s)",
                event.id,
                event.event_type.value,
            )
            return []
