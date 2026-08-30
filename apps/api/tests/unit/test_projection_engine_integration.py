import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.infrastructure.persistence.models.tenant import Tenant

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
@pytest.mark.requires_db
async def test_projection_engine_uses_skip_locked_and_subject_type_filtering(db_session):
    """Smoke test: engine can run one cycle and call get_events_since_seq with subject_type."""
    # projection_definition.tenant_id is a real foreign key, and row-level security
    # needs the session pointed at that tenant before either write is allowed.
    tenant_id = "ptest_t1"
    await db_session.execute(
        text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
    )
    db_session.add(
        Tenant(id=tenant_id, code="ptest-t1", name="Projection Test", status="Active")
    )
    await db_session.flush()

    repo = ProjectionRepository(db_session)
    event_repo = EventRepository(db_session)
    registry = ProjectionRegistry()

    # Register a dummy projection handler.
    async def handler(state: dict, event):
        state["count"] = state.get("count", 0) + 1
        return state

    registry.register("dummy", 1, "account", handler)

    # Create definition row.
    defn = await repo.create(
        tenant_id=tenant_id,
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
@pytest.mark.requires_db
async def test_query_projection_use_case_batches_over_events(db_session, monkeypatch):
    """QueryProjectionUseCase.get_state_as_of should batch over get_events_chronological."""
    projection_repo = AsyncMock()
    event_repo = AsyncMock(spec=EventRepository)
    registry = ProjectionRegistry()

    async def handler(state: dict, event):
        state["seen"] = state.get("seen", 0) + 1
        return state

    registry.register("dummy_query", 1, None, handler)
    use_case = QueryProjectionUseCase(
        projection_repo=projection_repo,
        event_repo=event_repo,
        registry=registry,
    )

    class Ev:
        def __init__(self, eid: str):
            self.id = eid

    # get_state_as_of pages with a batch size of 500 and stops as soon as a page
    # comes back short, so the first page has to be exactly full for the loop to go
    # round again. An earlier version of this test used pages of 2 and 1, which
    # stopped after the first page and never exercised the batching it was named for.
    BATCH_SIZE = 500
    event_repo.get_events_chronological.side_effect = [
        [Ev(f"e{i}") for i in range(BATCH_SIZE)],
        [Ev("last")],
        [],
    ]

    state = await use_case.get_state_as_of(
        tenant_id="t1",
        name="dummy_query",
        version=1,
        subject_id="s1",
        as_of=None,
    )
    assert state == {"seen": BATCH_SIZE + 1}


