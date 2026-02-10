"""Event repository. Append-only; no update. Returns application DTOs."""

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event import EventResult, EventToPersist
from app.infrastructure.persistence.models.event import Event
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.schemas.event import EventCreate


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
    )


class EventRepository(BaseRepository[Event]):
    """Event repository. Events are immutable after creation."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Event)

    async def get_last_hash(self, subject_id: str, tenant_id: str) -> str | None:
        result = await self.db.execute(
            select(Event.hash)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_time))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_last_event(self, subject_id: str, tenant_id: str) -> EventResult | None:
        result = await self.db.execute(
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_time))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _event_to_result(row) if row else None

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
            .order_by(Event.event_time.desc())
            .offset(skip)
            .limit(limit)
        )
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
            .order_by(Event.created_at.desc())
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
            )
            for e in events
        ]
        self.db.add_all(objs)
        await self.db.flush()
        for o in objs:
            await self.db.refresh(o)
        return [_event_to_result(o) for o in objs]
