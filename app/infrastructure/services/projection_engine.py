"""Projection engine: polls new events and advances projections via handlers (Phase 5)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.application.dtos.event import EventResult
from app.application.dtos.projection import ProjectionDefinitionResult
from app.core.projections import ProjectionRegistry

if TYPE_CHECKING:
    from app.application.interfaces.repositories import IEventRepository, IProjectionRepository

logger = logging.getLogger(__name__)


class ProjectionEngine:
    """Polls new events and advances active projections via registered handlers."""

    def __init__(
        self,
        projection_repo: "IProjectionRepository",
        event_repo: "IEventRepository",
        registry: ProjectionRegistry,
        *,
        interval_seconds: int = 5,
        batch_size: int = 1000,
    ) -> None:
        self._projection_repo = projection_repo
        self._event_repo = event_repo
        self._registry = registry
        self._interval = interval_seconds
        self._batch_size = batch_size

    async def run_once(self) -> None:
        """Run a single engine cycle: advance all projections once."""
        try:
            await self._advance_all()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ProjectionEngine cycle error")

    async def run(self) -> None:
        """Run the engine loop: advance all projections, then sleep."""
        while True:
            await self.run_once()
            await asyncio.sleep(self._interval)

    async def _advance_all(self) -> None:
        """Advance each active projection; workers coordinate via SKIP LOCKED."""
        definitions = await self._projection_repo.list_active_for_advance(
            tenant_id=None,
            limit=self._batch_size,
        )
        results = await asyncio.gather(
            *[self._advance_one(defn) for defn in definitions],
            return_exceptions=True,
        )
        for defn, r in zip(definitions, results):
            if isinstance(r, Exception):
                logger.exception(
                    "ProjectionEngine advance failed for %s/%s: %s",
                    defn.name,
                    defn.version,
                    r,
                )

    async def _advance_one(
        self, defn: ProjectionDefinitionResult
    ) -> None:
        """Advance one projection: lock, fetch events, apply handlers, upsert state, advance watermark."""
        registration = self._registry.get(defn.name, defn.version)
        if registration is None:
            return

        events = await self._event_repo.get_events_since_seq(
            tenant_id=defn.tenant_id,
            since_seq=defn.last_event_seq,
            limit=self._batch_size,
            subject_type=defn.subject_type,
        )
        if not events:
            return

        by_subject: dict[str, list[EventResult]] = {}
        for event in events:
            if event.event_seq is None:
                logger.warning(
                    "Skipping event %s with null event_seq; cannot advance watermark",
                    event.id,
                )
                continue
            by_subject.setdefault(event.subject_id, []).append(event)

        for subject_id, subject_events in by_subject.items():
            current = await self._projection_repo.get_state(defn.id, subject_id)
            state: dict = dict(current.state) if current else {}
            for event in subject_events:
                state = await registration.handler(state, event)
            await self._projection_repo.upsert_state(defn.id, subject_id, state)

        max_seq = max(e.event_seq for e in events if e.event_seq is not None)
        await self._projection_repo.advance_watermark(defn.id, max_seq)
