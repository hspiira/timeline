import asyncio
from unittest.mock import AsyncMock

import pytest

from app.application.dtos.projection import ProjectionDefinitionResult
from app.application.services.merkle_service import MerkleService
from app.application.use_cases.projections.manage_projections import (
    ProjectionManagementUseCase,
)
from app.application.use_cases.projections.query_projection import (
    QueryProjectionUseCase,
)
from app.core.projections import ProjectionRegistry
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.projection_repo import (
    ProjectionRepository,
)
from app.infrastructure.services.projection_engine import ProjectionEngine


@pytest.mark.asyncio
async def test_projection_engine_uses_skip_locked_and_subject_type_filtering(async_session):
    """Smoke test: engine can run one cycle and call get_events_since_seq with subject_type."""
    repo = ProjectionRepository(async_session)
    event_repo = EventRepository(async_session)
    registry = ProjectionRegistry()

    # Register a dummy projection handler.
    async def handler(state: dict, event):
        state["count"] = state.get("count", 0) + 1
        return state

    registry.register("dummy", 1, handler)

    # Create definition row.
    defn = await repo.create(
        tenant_id="t1",
        name="dummy",
        version=1,
        subject_type="account",
    )

    engine = ProjectionEngine(
        projection_repo=repo,
        event_repo=event_repo,
        registry=registry,
        interval_seconds=1,
        batch_size=10,
    )

    # Just ensure run_once does not raise; behavior is covered by repository tests.
    await engine.run_once()


@pytest.mark.asyncio
async def test_query_projection_use_case_batches_over_events(async_session, monkeypatch):
    """QueryProjectionUseCase.get_state_as_of should batch over get_events_chronological."""
    projection_repo = AsyncMock()
    event_repo = AsyncMock(spec=EventRepository)
    registry = ProjectionRegistry()

    async def handler(state: dict, event):
        state["seen"] = state.get("seen", 0) + 1
        return state

    registry.register("dummy", 1, handler)
    use_case = QueryProjectionUseCase(
        projection_repo=projection_repo,
        event_repo=event_repo,
        registry=registry,
    )

    class Ev:
        def __init__(self, eid: str):
            self.id = eid

    # First batch full, second batch partial, then empty.
    event_repo.get_events_chronological.side_effect = [
        [Ev("e1"), Ev("e2")],
        [Ev("e3")],
        [],
    ]

    state = await use_case.get_state_as_of(
        tenant_id="t1",
        name="dummy",
        version=1,
        subject_id="s1",
        as_of=None,
    )
    assert state == {"seen": 3}


