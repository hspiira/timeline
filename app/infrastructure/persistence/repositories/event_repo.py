"""Event repository. Append-only; no update. Returns application DTOs."""

from datetime import datetime

from sqlalchemy import asc, desc, func, select
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
    )


class EventRepository(BaseRepository[Event]):
    """Event repository. Events are immutable after creation."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Event)

    async def update(self, obj: Event) -> Event:
        raise NotImplementedError("Events are immutable and cannot be updated")

    async def delete(self, obj: Event) -> None:
        raise NotImplementedError("Events are immutable and cannot be deleted")

    async def get_last_hash(self, subject_id: str, tenant_id: str) -> str | None:
        result = await self.db.execute(
            select(Event.hash)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_time), desc(Event.id))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_last_event(self, subject_id: str, tenant_id: str) -> EventResult | None:
        result = await self.db.execute(
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_time), desc(Event.id))
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
            .order_by(Event.subject_id, desc(Event.event_time), desc(Event.id))
        )
        rows = result.scalars().all()
        # First row per subject_id is the latest (ordered by event_time desc, id desc).
        out: dict[str, EventResult | None] = dict.fromkeys(subject_ids)
        for e in rows:
            if out.get(e.subject_id) is None:
                out[e.subject_id] = _event_to_result(e)
        return out

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
            .order_by(desc(Event.event_time), desc(Event.id))
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
            after_event = await self.get_by_id(after_event_id)
            if not after_event:
                return []
            if after_event.subject_id != subject_id or after_event.tenant_id != tenant_id:
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
            .order_by(desc(Event.event_time), desc(Event.id))
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
            .order_by(desc(Event.event_time), desc(Event.id))
            .offset(skip)
            .limit(limit)
        )
        return [_event_to_result(e) for e in result.scalars().all()]

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
            )
            for e in events
        ]
        self.db.add_all(objs)
        await self.db.flush()
        # IDs and fields are set in Python (CUID + payload); no refresh needed.
        return [_event_to_result(o) for o in objs]
