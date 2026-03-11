"""Event enrichment: inject correlation_id, actor/request_id, source from request context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.application.dtos.event import EventCreate


@dataclass
class EnrichmentContext:
    """Context for API-originated events (enrichers use this to fill in metadata)."""

    tenant_id: str
    actor_id: str | None
    request_id: str | None
    source_ip: str | None


class IEventEnricher(Protocol):
    """Protocol for event enrichers (run in order: correlation, actor, source)."""

    async def enrich(self, event: EventCreate, context: EnrichmentContext) -> EventCreate:
        """Return a copy of the event with enrichment applied (non-destructive where possible)."""
        ...


class CorrelationEnricher:
    """Set correlation_id to a new UUID4 if the event has none."""

    async def enrich(self, event: EventCreate, context: EnrichmentContext) -> EventCreate:
        if event.correlation_id:
            return event
        return event.model_copy(update={"correlation_id": str(uuid.uuid4())})


class ActorEnricher:
    """Inject actor_id and request_id into payload['_meta']; merge into existing _meta if present."""

    async def enrich(self, event: EventCreate, context: EnrichmentContext) -> EventCreate:
        existing_meta = event.payload.get("_meta", {})
        if existing_meta and not isinstance(existing_meta, dict):
            return event
        meta = dict(existing_meta)
        if context.actor_id is not None:
            meta.setdefault("actor_id", context.actor_id)
        if context.request_id is not None:
            meta.setdefault("request_id", context.request_id)
        if meta == existing_meta:
            return event
        payload = {**event.payload, "_meta": meta}
        return event.model_copy(update={"payload": payload})


class SourceEnricher:
    """Set source to 'api:<actor_id>' for API-originated events that have no source."""

    async def enrich(self, event: EventCreate, context: EnrichmentContext) -> EventCreate:
        if event.source:
            return event
        actor = context.actor_id or "anonymous"
        return event.model_copy(update={"source": f"api:{actor}"})
