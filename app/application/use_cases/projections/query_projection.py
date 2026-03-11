"""Query projection use case: current state, as_of replay, list states (Phase 5)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.application.dtos.projection import ProjectionStateResult

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IEventRepository,
        IProjectionRepository,
    )
    from app.core.projections import ProjectionRegistry


class QueryProjectionUseCase:
    """Read projection state (current or point-in-time via replay)."""

    def __init__(
        self,
        projection_repo: "IProjectionRepository",
        event_repo: "IEventRepository",
        registry: "ProjectionRegistry",
    ) -> None:
        self._projection_repo = projection_repo
        self._event_repo = event_repo
        self._registry = registry

    async def get_current_state(
        self,
        tenant_id: str,
        name: str,
        version: int,
        subject_id: str,
    ) -> dict | None:
        """Return current projection state for (name, version, subject_id), or None."""
        defn = await self._projection_repo.get_by_name_version(
            tenant_id=tenant_id, name=name, version=version
        )
        if not defn:
            return None
        state = await self._projection_repo.get_state(defn.id, subject_id)
        return state.state if state else None

    async def get_state_as_of(
        self,
        tenant_id: str,
        name: str,
        version: int,
        subject_id: str,
        as_of: datetime,
    ) -> dict | None:
        """Replay events through handler up to as_of; does not use projection_state table."""
        registration = self._registry.get(name, version)
        if not registration:
            return None
        events = await self._event_repo.get_events_chronological(
            subject_id=subject_id,
            tenant_id=tenant_id,
            as_of=as_of,
            limit=10000,
        )
        state: dict = {}
        for event in events:
            state = await registration.handler(state, event)
        return state

    async def list_all_states(
        self,
        tenant_id: str,
        name: str,
        version: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ProjectionStateResult]:
        """List all subjects' current state for this projection (paginated)."""
        defn = await self._projection_repo.get_by_name_version(
            tenant_id=tenant_id, name=name, version=version
        )
        if not defn:
            return []
        return await self._projection_repo.list_states(
            projection_id=defn.id, skip=skip, limit=limit
        )
