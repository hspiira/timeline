"""Event repository. Append-only; no update. Returns application DTOs."""

from datetime import datetime

from sqlalchemy import asc, desc, func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event import EventCreate, EventResult, EventToPersist
from app.infrastructure.persistence.models.event import Event
from app.infrastructure.persistence.repositories.base import BaseRepository


def _event_to_result(e: Event) -> EventResult:
    """Map ORM Event to application EventResult."""
    return EventResult(
        id=e.id,
        tenant_id=e.tenant_id,
        subject_id=e.subject_id,
        event_type=e.event_type,
        schema_version=e.schema_version,
        event_time=e.event_time,
        payload=e.payload,
        previous_hash=e.previous_hash,
        hash=e.hash,
        workflow_instance_id=e.workflow_instance_id,
        correlation_id=e.correlation_id,
        external_id=e.external_id,
        source=e.source,
        event_seq=e.event_seq,
    )


class EventRepository(BaseRepository[Event]):
    """Event repository. Events are immutable after creation."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Event)

    async def update(self, obj: Event) -> Event:
        raise NotImplementedError("Events are immutable and cannot be updated")

    async def delete(self, obj: Event) -> None:
        raise NotImplementedError("Events are immutable and cannot be deleted")

    async def lock_subject_for_update(self, subject_id: str) -> None:
        """Acquire row-level exclusive lock on the subject row for the current transaction."""
        await self.db.execute(
            text("SELECT id FROM subject WHERE id = :sid FOR UPDATE"),
            {"sid": subject_id},
        )

    async def get_last_event(self, subject_id: str, tenant_id: str) -> EventResult | None:
        # event_seq is monotonic insertion order (created_at is transaction-scoped in PostgreSQL).
        result = await self.db.execute(
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_seq))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _event_to_result(row) if row else None

    async def get_last_events_for_subjects(
        self, tenant_id: str, subject_ids: set[str]
    ) -> dict[str, EventResult | None]:
        """Return the latest event per subject (batch; one query). Missing subjects have None."""
        if not subject_ids:
            return {}
        result = await self.db.execute(
            select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.subject_id.in_(subject_ids),
            )
            .order_by(Event.subject_id, desc(Event.event_seq))
        )
        rows = result.scalars().all()
        # First row per subject_id is the latest (ordered by event_seq).
        out: dict[str, EventResult | None] = dict.fromkeys(subject_ids)
        for e in rows:
            if out.get(e.subject_id) is None:
                out[e.subject_id] = _event_to_result(e)
        return out

    async def get_by_subject_and_external_id(
        self, subject_id: str, tenant_id: str, external_id: str
    ) -> EventResult | None:
        """Return event by subject and external idempotency key, if any."""
        result = await self.db.execute(
            select(Event).where(
                Event.subject_id == subject_id,
                Event.tenant_id == tenant_id,
                Event.external_id == external_id,
            )
        )
        row = result.scalar_one_or_none()
        return _event_to_result(row) if row else None

    async def get_by_external_ids(
        self, tenant_id: str, subject_external_pairs: set[tuple[str, str]]
    ) -> dict[tuple[str, str], EventResult]:
        """Return existing events for (subject_id, external_id) pairs."""
        if not subject_external_pairs:
            return {}
        result = await self.db.execute(
            select(Event).where(
                Event.tenant_id == tenant_id,
                tuple_(Event.subject_id, Event.external_id).in_(
                    list(subject_external_pairs)
                ),
            )
        )
        rows = result.scalars().all()
        return {(e.subject_id, e.external_id): _event_to_result(e) for e in rows}

    async def create_event(
        self,
        tenant_id: str,
        data: EventCreate,
        event_hash: str,
        previous_hash: str | None,
    ) -> EventResult:
        event = Event(
            tenant_id=tenant_id,
            subject_id=data.subject_id,
            event_type=data.event_type,
            schema_version=data.schema_version,
            event_time=data.event_time,
            payload=data.payload,
            hash=event_hash,
            previous_hash=previous_hash,
            workflow_instance_id=data.workflow_instance_id,
            correlation_id=data.correlation_id,
            external_id=data.external_id,
            source=data.source,
        )
        created = await self.create(event)
        return _event_to_result(created)

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventResult]:
        result = await self.db.execute(
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_seq))
            .offset(skip)
            .limit(limit)
        )
        return [_event_to_result(e) for e in result.scalars().all()]

    async def get_events_chronological(
        self,
        subject_id: str,
        tenant_id: str,
        as_of: datetime | None = None,
        after_event_id: str | None = None,
        workflow_instance_id: str | None = None,
        limit: int = 10000,
    ) -> list[EventResult]:
        """Return events for subject in chronological order (oldest first). If as_of is set, only events with event_time <= as_of. If after_event_id is set, only events after that event (for snapshot replay). If workflow_instance_id is set, only events in that stream."""
        q = (
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
        )
        if workflow_instance_id is not None:
            q = q.where(Event.workflow_instance_id == workflow_instance_id)
        if as_of is not None:
            q = q.where(Event.event_time <= as_of)
        if after_event_id is not None:
            after_event = await self.get_by_id_and_tenant(after_event_id, tenant_id)
            if not after_event:
                return []
            if after_event.subject_id != subject_id:
                raise ValueError(
                    f"after_event_id {after_event_id!r} does not belong to subject_id={subject_id!r}, tenant_id={tenant_id!r}"
                )
            q = q.where(
                (Event.event_time > after_event.event_time)
                | (
                    (Event.event_time == after_event.event_time)
                    & (Event.id > after_event_id)
                )
            )
        q = q.order_by(asc(Event.event_time), asc(Event.id)).limit(limit)
        result = await self.db.execute(q)
        return [_event_to_result(e) for e in result.scalars().all()]

    async def count_by_subject(self, subject_id: str, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Event.id)).where(
                Event.subject_id == subject_id,
                Event.tenant_id == tenant_id,
            )
        )
        return result.scalar() or 0

    async def count_by_tenant(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Event.id)).where(Event.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_counts_by_type(self, tenant_id: str) -> dict[str, int]:
        """Return event counts per event_type for tenant."""
        result = await self.db.execute(
            select(Event.event_type, func.count(Event.id))
            .where(Event.tenant_id == tenant_id)
            .group_by(Event.event_type)
        )
        return dict(result.all())

    async def get_by_id(self, event_id: str) -> EventResult | None:
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        row = result.scalar_one_or_none()
        return _event_to_result(row) if row else None

    async def get_by_id_and_tenant(self, event_id: str, tenant_id: str) -> EventResult | None:
        result = await self.db.execute(
            select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
        )
        row = result.scalar_one_or_none()
        return _event_to_result(row) if row else None

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventResult]:
        result = await self.db.execute(
            select(Event)
            .where(Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_seq))
            .offset(skip)
            .limit(limit)
        )
        return [_event_to_result(e) for e in result.scalars().all()]

    async def get_by_workflow_instance_id(
        self,
        tenant_id: str,
        workflow_instance_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventResult]:
        """Return events for a flow (workflow_instance_id) across all subjects, newest first."""
        result = await self.db.execute(
            select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.workflow_instance_id == workflow_instance_id,
            )
            .order_by(desc(Event.event_seq))
            .offset(skip)
            .limit(limit)
        )
        return [_event_to_result(e) for e in result.scalars().all()]

    async def get_chain_tip_hash(self, tenant_id: str) -> str | None:
        """Return the hash of the latest event for the tenant (chain tip). None if no events. Uses event_seq for insertion order."""
        result = await self.db.execute(
            select(Event.hash)
            .where(Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_seq))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row else None

    async def get_events_since_seq(
        self,
        tenant_id: str,
        since_seq: int,
        limit: int = 1000,
    ) -> list[EventResult]:
        """Return events for tenant with event_seq > since_seq, ordered by event_seq asc (for projection engine watermark polling)."""
        result = await self.db.execute(
            select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.event_seq > since_seq,
            )
            .order_by(asc(Event.event_seq))
            .limit(limit)
        )
        events = [_event_to_result(e) for e in result.scalars().all()]
        for ev in events:
            if ev.event_seq is None:
                raise ValueError(
                    "event_seq is required for sequence-backed read; "
                    "missing repository mapping or backfill"
                )
        return events

    async def get_distinct_tenant_ids(self) -> list[str]:
        """Return distinct tenant_ids that have at least one event (for anchoring job). Deterministic order by tenant_id."""
        result = await self.db.execute(
            select(Event.tenant_id).distinct().order_by(Event.tenant_id)
        )
        return list(result.scalars().all())

    async def create_events_bulk(
        self, tenant_id: str, events: list[EventToPersist]
    ) -> list[EventResult]:
        if not events:
            return []
        objs = [
            Event(
                tenant_id=tenant_id,
                subject_id=e.subject_id,
                event_type=e.event_type,
                schema_version=e.schema_version,
                event_time=e.event_time,
                payload=e.payload,
                hash=e.hash,
                previous_hash=e.previous_hash,
                workflow_instance_id=e.workflow_instance_id,
                correlation_id=e.correlation_id,
                external_id=e.external_id,
                source=e.source,
            )
            for e in events
        ]
        self.db.add_all(objs)
        await self.db.flush()
        # Refresh so server-generated event_seq is loaded (server_default=nextval).
        for o in objs:
            await self.db.refresh(o)
        return [_event_to_result(o) for o in objs]
