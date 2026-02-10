"""Event repository. Append-only; no update."""

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event import EventToPersist
from app.infrastructure.persistence.models.event import Event
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.schemas.event import EventCreate


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

    async def get_last_event(self, subject_id: str, tenant_id: str) -> Event | None:
        result = await self.db.execute(
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(desc(Event.event_time))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_event(
        self,
        tenant_id: str,
        data: EventCreate,
        event_hash: str,
        previous_hash: str | None,
    ) -> Event:
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
        return await self.create(event)

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .where(Event.subject_id == subject_id, Event.tenant_id == tenant_id)
            .order_by(Event.event_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

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

    async def get_by_id_and_tenant(self, event_id: str, tenant_id: str) -> Event | None:
        result = await self.db.execute(
            select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .where(Event.tenant_id == tenant_id)
            .order_by(Event.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_events_bulk(
        self, tenant_id: str, events: list[EventToPersist]
    ) -> list[Event]:
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
        return objs
