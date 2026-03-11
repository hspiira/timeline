"""Event creation use case: single and bulk with hash chaining and optional schema validation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.application.dtos.event import EventCreate, EventResult, EventToPersist
from app.application.services.enrichment import EnrichmentContext
from app.application.dtos.subject_type import SubjectTypeResult
from app.application.interfaces.post_create_hooks import IPostCreateHook, PostCreateContext
from app.application.interfaces.repositories import (
    IEventRepository,
    ISubjectRepository,
)
from app.application.interfaces.services import IHashService
from app.application.services.enrichment import IEventEnricher
from app.domain.entities.event import EventEntity
from app.domain.exceptions import (
    ChainForkError,
    ResourceNotFoundException,
    ValidationException,
)
from app.domain.value_objects.core import EventChain, EventType, Hash
from app.shared.telemetry.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.application.interfaces.repositories import ISubjectTypeRepository
    from app.application.interfaces.services import (
        IEventSchemaValidator,
        IEventTransitionValidator,
    )


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
        workflow_instance_id=r.workflow_instance_id,
        correlation_id=r.correlation_id,
        external_id=r.external_id,
        source=r.source,
    )


logger = get_logger(__name__)

MAX_RETRIES = 3


class EventService:
    """Creates events with hash chaining and optional schema validation (IEventService)."""

    def __init__(
        self,
        event_repo: IEventRepository,
        hash_service: IHashService,
        subject_repo: ISubjectRepository,
        *,
        db: "AsyncSession",
        schema_validator: IEventSchemaValidator | None = None,
        transition_validator: IEventTransitionValidator | None = None,
        subject_type_repo: "ISubjectTypeRepository | None" = None,
        enrichers: list[IEventEnricher] | None = None,
        post_create_hooks: list[IPostCreateHook] | None = None,
    ) -> None:
        self.event_repo = event_repo
        self.hash_service = hash_service
        self.subject_repo = subject_repo
        self.db = db
        self.schema_validator = schema_validator
        self.transition_validator = transition_validator
        self.subject_type_repo = subject_type_repo
        self.enrichers = enrichers or []
        self._post_create_hooks = post_create_hooks or []

    async def create_event(
        self,
        tenant_id: str,
        data: EventCreate,
        *,
        trigger_workflows: bool = True,
        skip_transition_validation: bool = False,
        skip_schema_validation: bool = False,
        enrichment_context: EnrichmentContext | None = None,
    ) -> EventEntity:
        """Create one event; validate subject and schema, compute hash, optionally trigger workflows."""
        if data.external_id:
            existing = await self.event_repo.get_by_subject_and_external_id(
                data.subject_id, tenant_id, data.external_id
            )
            if existing:
                return _event_result_to_entity(existing)

        subject = await self.subject_repo.get_by_id_and_tenant(
            data.subject_id, tenant_id
        )
        if not subject:
            raise ResourceNotFoundException("subject", data.subject_id)

        if self.subject_type_repo:
            type_config = await self.subject_type_repo.get_by_tenant_and_type(
                tenant_id, subject.subject_type.value
            )
            if type_config and type_config.allowed_event_types:
                if data.event_type not in type_config.allowed_event_types:
                    raise ValidationException(
                        f"Event type '{data.event_type}' is not allowed for subject type '{subject.subject_type.value}'. "
                        f"Allowed: {', '.join(type_config.allowed_event_types)}",
                        field="event_type",
                    )

        if not skip_schema_validation and self.schema_validator:
            await self.schema_validator.validate_payload(
                tenant_id,
                data.event_type,
                data.schema_version,
                data.payload,
                subject_type=subject.subject_type.value,
            )

        if not skip_transition_validation and self.transition_validator:
            await self.transition_validator.validate_can_emit(
                tenant_id=tenant_id,
                subject_id=data.subject_id,
                event_type=data.event_type,
                workflow_instance_id=data.workflow_instance_id,
            )

        if enrichment_context and self.enrichers:
            for enricher in self.enrichers:
                data = await enricher.enrich(data, enrichment_context)

        for attempt in range(MAX_RETRIES):
            try:
                async with self.db.begin():
                    await self.event_repo.lock_subject_for_update(data.subject_id)
                    prev_event = await self.event_repo.get_last_event(
                        data.subject_id, tenant_id
                    )
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
                break
            except IntegrityError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ChainForkError(
                        "Could not append event after retries.",
                        data.subject_id,
                    ) from exc
                await asyncio.sleep(0.05 * (2**attempt))

        entity = _event_result_to_entity(created)
        context = PostCreateContext(
            tenant_id=tenant_id,
            entity=entity,
            event_result=created,
            subject_type=subject.subject_type.value,
            trigger_workflows=trigger_workflows,
        )
        for hook in self._post_create_hooks:
            await hook.after_event(context)
        return entity

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list[EventCreate],
        *,
        skip_schema_validation: bool = False,
        trigger_workflows: bool = False,
        enrichment_context: EnrichmentContext | None = None,
    ) -> list[EventEntity]:
        """Bulk create events (e.g. email sync). Hashes computed sequentially; single DB roundtrip."""
        if not events:
            return []

        seen_entities: list[EventEntity] = []
        pairs = {(e.subject_id, e.external_id) for e in events if e.external_id}
        if pairs:
            already_seen = await self.event_repo.get_by_external_ids(tenant_id, pairs)
            new_events = [
                e for e in events if (e.subject_id, e.external_id) not in already_seen
            ]
            seen_entities = [_event_result_to_entity(r) for r in already_seen.values()]
            if not new_events:
                return seen_entities
            events = new_events

        subject_ids = {e.subject_id for e in events}
        subjects = await self.subject_repo.get_by_ids_and_tenant(tenant_id, subject_ids)
        subject_by_id = {s.id: s for s in subjects}
        for sid in subject_ids:
            if sid not in subject_by_id:
                raise ResourceNotFoundException("subject", sid)

        if self.subject_type_repo:
            unique_types = {s.subject_type.value for s in subjects}
            type_config_by_name: dict[str, SubjectTypeResult] = {}
            for type_name in unique_types:
                config = await self.subject_type_repo.get_by_tenant_and_type(
                    tenant_id, type_name
                )
                if config:
                    type_config_by_name[type_name] = config
            for event_data in events:
                subject = subject_by_id[event_data.subject_id]
                type_config = type_config_by_name.get(subject.subject_type.value)
                if type_config and type_config.allowed_event_types:
                    if event_data.event_type not in type_config.allowed_event_types:
                        raise ValidationException(
                            f"Event type '{event_data.event_type}' is not allowed for subject type '{subject.subject_type.value}'. "
                            f"Allowed: {', '.join(type_config.allowed_event_types)}",
                            field="event_type",
                        )

        if enrichment_context and self.enrichers:
            enriched: list[EventCreate] = []
            for event_data in events:
                for enricher in self.enrichers:
                    event_data = await enricher.enrich(event_data, enrichment_context)
                enriched.append(event_data)
            events = enriched

        representative_subject_id = min(subject_ids)

        for attempt in range(MAX_RETRIES):
            try:
                async with self.db.begin():
                    for subject_id in sorted(subject_ids):
                        await self.event_repo.lock_subject_for_update(subject_id)
                    last_events = await self.event_repo.get_last_events_for_subjects(
                        tenant_id, subject_ids
                    )
                    chain_state: dict[str, tuple[str | None, datetime | None]] = {
                        sid: (
                            (last_events[sid].hash, last_events[sid].event_time)
                            if last_events.get(sid)
                            else (None, None)
                        )
                        for sid in subject_ids
                    }

                    to_persist: list[EventToPersist] = []
                    for event_data in events:
                        prev_hash, prev_time = chain_state[event_data.subject_id]
                        EventEntity.validate_event_time_after_previous(
                            event_data.event_time,
                            prev_time,
                        )
                        if self.transition_validator:
                            await self.transition_validator.validate_can_emit(
                                tenant_id=tenant_id,
                                subject_id=event_data.subject_id,
                                event_type=event_data.event_type,
                                workflow_instance_id=event_data.workflow_instance_id,
                            )
                        if not skip_schema_validation and self.schema_validator:
                            subject = subject_by_id[event_data.subject_id]
                            await self.schema_validator.validate_payload(
                                tenant_id,
                                event_data.event_type,
                                event_data.schema_version,
                                event_data.payload,
                                subject_type=subject.subject_type.value,
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
                                workflow_instance_id=event_data.workflow_instance_id,
                                correlation_id=event_data.correlation_id,
                                external_id=event_data.external_id,
                                source=event_data.source,
                            )
                        )
                        chain_state[event_data.subject_id] = (
                            event_hash,
                            event_data.event_time,
                        )

                    created = await self.event_repo.create_events_bulk(
                        tenant_id, to_persist
                    )
                break
            except IntegrityError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ChainForkError(
                        "Could not append events after retries.",
                        representative_subject_id,
                    ) from exc
                await asyncio.sleep(0.05 * (2**attempt))

        entities = [_event_result_to_entity(ev) for ev in created]
        if pairs:
            entities = seen_entities + entities

        for ev, entity in zip(created, entities):
            subject = subject_by_id[ev.subject_id]
            context = PostCreateContext(
                tenant_id=tenant_id,
                entity=entity,
                event_result=ev,
                subject_type=subject.subject_type.value,
                trigger_workflows=trigger_workflows,
            )
            for hook in self._post_create_hooks:
                await hook.after_event(context)
        return entities
