"""Event creation use case: single and bulk with hash chaining and optional schema validation."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import IntegrityError

from app.application.dtos.event import EventCreate, EventResult
from app.application.dtos.integrity import OpenEpochAssignment
from app.application.services.enrichment import EnrichmentContext
from app.application.interfaces.post_create_hooks import IPostCreateHook, PostCreateContext
from app.application.interfaces.repositories import (
    IEventRepository,
    ISubjectRepository,
)
from app.application.interfaces.services import IHashService
from app.application.services.enrichment import IEventEnricher
from app.application.services.tsa_batch_queue import (
    TsaBatchQueue,
    TsaBatchItem,
    DEFAULT_TSA_BATCH_QUEUE,
)
from app.domain.entities.event import EventEntity
from app.domain.enums import EventIntegrityStatus, IntegrityProfile
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
    from app.application.services.epoch_service import EpochService


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
        epoch_service: "EpochService | None" = None,
        tsa_batch_queue: TsaBatchQueue | None = DEFAULT_TSA_BATCH_QUEUE,
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
        self.epoch_service = epoch_service
        self._tsa_batch_queue = tsa_batch_queue

    async def _append_one_for_epoch(
        self,
        assignment: OpenEpochAssignment,
        tenant_id: str,
        data: EventCreate,
        event_hash: str,
        prev_hash: str | None,
    ) -> tuple[EventResult, bool]:
        """Persist one event into the given epoch; used by with_open_epoch. Returns (created, is_first)."""
        profile = IntegrityProfile(assignment.profile_snapshot)
        integrity_status = (
            EventIntegrityStatus.VALID.value
            if profile == IntegrityProfile.STANDARD
            else EventIntegrityStatus.PENDING_ANCHOR.value
        )
        merkle_leaf_hash = (
            event_hash if profile == IntegrityProfile.LEGAL_GRADE else None
        )
        created = await self.event_repo.create_event(
            tenant_id,
            data,
            event_hash,
            prev_hash,
            epoch_id=assignment.epoch_id,
            integrity_status=integrity_status,
            merkle_leaf_hash=merkle_leaf_hash,
        )
        if self._tsa_batch_queue and profile == IntegrityProfile.COMPLIANCE:
            await self._tsa_batch_queue.enqueue(
                TsaBatchItem(
                    tenant_id=tenant_id,
                    event_id=created.id,
                    payload_hash_hex=event_hash,
                )
            )
        return created, assignment.event_count == 0

    async def _release_ambient_transaction(self) -> None:
        """Close any transaction opened before this write, so it can open its own.

        Row-level security needs the tenant context, which is set with SET LOCAL and
        so only exists inside a transaction — meaning the session handed over by
        get_db already has one open. This write needs its own, because a chain fork is
        retried by rolling the whole attempt back and a savepoint inside someone
        else's transaction would not do.

        Everything this method does before this point is reads, so closing that
        transaction loses nothing of its own. Without this, SQLAlchemy raises "a
        transaction is already begun on this Session" and every event creation fails
        with a 500 — which it did, on both the API and the seed scripts, with nothing
        covering it.

        Caller beware: this rolls back, so any of the *caller's* uncommitted writes on
        the same session are discarded. That is safe for the current callers, which
        take a session from ``get_db`` and write nothing before creating the event. A
        caller that does need to write first must commit before calling, or use a
        separate session for the event.

        The caller must re-apply the tenant context inside its new transaction, since
        SET LOCAL did not survive.
        """
        if self.db.in_transaction():
            await self.db.rollback()

    async def _find_existing_by_external_id(
        self, tenant_id: str, data: EventCreate
    ) -> EventEntity | None:
        """Return the already-ingested event for this external_id, if there is one."""
        if not data.external_id:
            return None
        existing = await self.event_repo.get_by_subject_and_external_id(
            data.subject_id, tenant_id, data.external_id
        )
        return _event_result_to_entity(existing) if existing else None

    async def _load_subject_or_raise(self, tenant_id: str, subject_id: str) -> Any:
        """Fetch the subject, or raise if it does not belong to this tenant."""
        subject = await self.subject_repo.get_by_id_and_tenant(subject_id, tenant_id)
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)
        return subject

    async def _validate_event_type_allowed(
        self, tenant_id: str, subject_type: str, event_type: str
    ) -> None:
        """Reject an event type the subject type does not permit."""
        if not self.subject_type_repo:
            return
        type_config = await self.subject_type_repo.get_by_tenant_and_type(
            tenant_id, subject_type
        )
        if not (type_config and type_config.allowed_event_types):
            return
        if event_type not in type_config.allowed_event_types:
            raise ValidationException(
                f"Event type '{event_type}' is not allowed for subject type '{subject_type}'. "
                f"Allowed: {', '.join(type_config.allowed_event_types)}",
                field="event_type",
            )

    async def _apply_enrichers(
        self, data: EventCreate, enrichment_context: EnrichmentContext | None
    ) -> EventCreate:
        """Run the configured enrichers over one event, in order."""
        if not (enrichment_context and self.enrichers):
            return data
        for enricher in self.enrichers:
            data = await enricher.enrich(data, enrichment_context)
        return data

    async def _run_post_create_hooks(
        self,
        tenant_id: str,
        entity: EventEntity,
        created: EventResult,
        subject_type: str,
        trigger_workflows: bool,
    ) -> None:
        """Notify the post-create hooks about one persisted event."""
        context = PostCreateContext(
            tenant_id=tenant_id,
            entity=entity,
            event_result=created,
            subject_type=subject_type,
            trigger_workflows=trigger_workflows,
        )
        for hook in self._post_create_hooks:
            await hook.after_event(context)

    async def _append_one(self, tenant_id: str, data: EventCreate) -> EventResult:
        """Append one event inside an already-open transaction with tenant context set."""
        await self.event_repo.lock_subject_for_update(data.subject_id)
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

        if not self.epoch_service:
            return await self.event_repo.create_event(
                tenant_id, data, event_hash, prev_hash
            )

        _, created = await self.epoch_service.with_open_epoch(
            tenant_id,
            data.subject_id,
            lambda a: self._append_one_for_epoch(
                a, tenant_id, data, event_hash, prev_hash
            ),
        )
        return created

    async def _append_with_retry(self, tenant_id: str, data: EventCreate) -> EventResult:
        """Append one event, retrying the whole transaction on a chain fork."""
        for attempt in range(MAX_RETRIES):
            try:
                await self._release_ambient_transaction()
                async with self.db.begin():
                    # SET LOCAL did not survive the release above; set it again so
                    # row-level security applies inside this transaction.
                    await self.event_repo.apply_tenant_context(tenant_id)
                    return await self._append_one(tenant_id, data)
            except IntegrityError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ChainForkError(
                        "Could not append event after retries.",
                        data.subject_id,
                    ) from exc
                await asyncio.sleep(0.05 * (2**attempt))
        raise AssertionError("unreachable: the final attempt either returns or raises")

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
        # The checks below read tenant-scoped tables before this method opens its own
        # transaction, so they need the tenant context in whatever transaction is
        # current. It is normally already set by get_db, but not on a second call on
        # the same session: the first call committed, taking its SET LOCAL with it.
        # Setting it here makes this method self-sufficient and repeatable.
        await self.event_repo.apply_tenant_context(tenant_id)

        already_ingested = await self._find_existing_by_external_id(tenant_id, data)
        if already_ingested:
            return already_ingested

        subject = await self._load_subject_or_raise(tenant_id, data.subject_id)
        subject_type = subject.subject_type.value
        await self._validate_event_type_allowed(tenant_id, subject_type, data.event_type)

        if not skip_schema_validation and self.schema_validator:
            await self.schema_validator.validate_payload(
                tenant_id,
                data.event_type,
                data.schema_version,
                data.payload,
                subject_type=subject_type,
            )

        if not skip_transition_validation and self.transition_validator:
            await self.transition_validator.validate_can_emit(
                tenant_id=tenant_id,
                subject_id=data.subject_id,
                event_type=data.event_type,
                workflow_instance_id=data.workflow_instance_id,
            )

        data = await self._apply_enrichers(data, enrichment_context)

        created = await self._append_with_retry(tenant_id, data)
        entity = _event_result_to_entity(created)
        await self._run_post_create_hooks(
            tenant_id, entity, created, subject_type, trigger_workflows
        )
        return entity
