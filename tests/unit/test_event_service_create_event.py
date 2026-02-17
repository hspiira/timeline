"""EventService.create_event unit tests with mocked repos."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.dtos.event import EventCreate, EventResult
from app.application.dtos.subject import SubjectResult
from app.application.use_cases.events import EventService
from app.domain.exceptions import ResourceNotFoundException
from app.domain.value_objects.core import SubjectType


def _event_create(
    subject_id: str = "sub1",
    event_type: str = "created",
    schema_version: int = 1,
) -> EventCreate:
    return EventCreate(
        subject_id=subject_id,
        event_type=event_type,
        schema_version=schema_version,
        event_time=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        payload={"name": "test"},
    )


def _event_result(
    subject_id: str = "sub1",
    event_type: str = "created",
    event_hash: str = "a" * 64,
    previous_hash: str | None = None,
) -> EventResult:
    return EventResult(
        id="ev1",
        tenant_id="t1",
        subject_id=subject_id,
        event_type=event_type,
        schema_version=1,
        event_time=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        payload={"name": "test"},
        previous_hash=previous_hash,
        hash=event_hash,
        workflow_instance_id=None,
        correlation_id=None,
    )


@pytest.fixture
def event_service_mocks():
    """EventService with mocked event_repo, hash_service, subject_repo (no schema/transition/workflow)."""
    event_repo = AsyncMock()
    hash_service = AsyncMock()
    hash_service.compute_hash = lambda *args, **kwargs: "a" * 64
    subject_repo = AsyncMock()
    subject_repo.get_by_id_and_tenant = AsyncMock(
        return_value=SubjectResult(
            id="sub1",
            tenant_id="t1",
            subject_type=SubjectType("client"),
            external_ref=None,
            display_name="Test",
            attributes={},
        )
    )
    event_repo.get_last_event = AsyncMock(return_value=None)
    event_repo.create_event = AsyncMock(
        return_value=_event_result(event_hash="a" * 64, previous_hash=None)
    )
    svc = EventService(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_validator=None,
        workflow_engine_provider=None,
        transition_validator=None,
    )
    return svc, event_repo, subject_repo


async def test_create_event_calls_repo_and_returns_entity(
    event_service_mocks,
) -> None:
    """create_event with valid data calls subject_repo, event_repo.get_last_event, event_repo.create_event and returns EventEntity."""
    svc, event_repo, subject_repo = event_service_mocks
    data = _event_create()

    entity = await svc.create_event("t1", data, trigger_workflows=False)

    assert entity.id == "ev1"
    assert entity.subject_id == "sub1"
    assert entity.event_type.value == "created"
    assert entity.payload == {"name": "test"}
    subject_repo.get_by_id_and_tenant.assert_awaited_once_with("sub1", "t1")
    event_repo.get_last_event.assert_awaited_once_with("sub1", "t1")
    event_repo.create_event.assert_awaited_once()
    call_kw = event_repo.create_event.call_args
    assert call_kw[0][0] == "t1"
    assert call_kw[0][1] == data
    assert call_kw[0][2] == "a" * 64
    assert call_kw[0][3] is None


async def test_create_event_subject_not_found_raises(
    event_service_mocks,
) -> None:
    """create_event when subject does not exist raises ResourceNotFoundException."""
    svc, event_repo, subject_repo = event_service_mocks
    subject_repo.get_by_id_and_tenant = AsyncMock(return_value=None)
    data = _event_create()

    with pytest.raises(ResourceNotFoundException) as exc_info:
        await svc.create_event("t1", data, trigger_workflows=False)

    assert exc_info.value.details.get("resource_type") == "subject"
    assert exc_info.value.details.get("resource_id") == "sub1"
    event_repo.create_event.assert_not_awaited()
