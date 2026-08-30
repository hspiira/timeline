"""Tests for EventTransitionValidator (mocked rule and event repos)."""

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.application.dtos.event_transition_rule import EventTransitionRuleResult
from app.application.services.event_transition_validator import EventTransitionValidator
from app.domain.exceptions import TransitionValidationException


@dataclass
class _MockEvent:
    """Minimal event-like object for validator (has event_type, payload, event_time)."""

    event_type: str
    payload: dict
    event_time: datetime


def _mock_rule(
    event_type: str,
    required_prior_event_types: list[str],
    *,
    prior_event_payload_conditions: dict | None = None,
    max_occurrences_per_stream: int | None = None,
    fresh_prior_event_type: str | None = None,
) -> EventTransitionRuleResult:
    return EventTransitionRuleResult(
        id="rule-1",
        tenant_id="t1",
        event_type=event_type,
        required_prior_event_types=required_prior_event_types,
        description=None,
        prior_event_payload_conditions=prior_event_payload_conditions,
        max_occurrences_per_stream=max_occurrences_per_stream,
        fresh_prior_event_type=fresh_prior_event_type,
    )


@pytest.fixture
def validator_with_mocks():
    """EventTransitionValidator with async mocks for rule_repo and event_repo."""

    class MockRuleRepo:
        def __init__(self, rule: EventTransitionRuleResult | None = None):
            self.rule = rule

        async def get_rule_for_event_type(self, tenant_id: str, event_type: str):
            return self.rule

    class MockEventRepo:
        def __init__(self, events: list[_MockEvent] | None = None):
            self.events = events or []

        async def get_events_chronological(
            self,
            subject_id: str,
            tenant_id: str,
            as_of=None,
            after_event_id=None,
            workflow_instance_id=None,
            limit=10000,
        ):
            return self.events

    def make_validator(
        rule: EventTransitionRuleResult | None = None,
        events: list[_MockEvent] | None = None,
    ) -> EventTransitionValidator:
        return EventTransitionValidator(
            rule_repo=MockRuleRepo(rule),
            event_repo=MockEventRepo(events),
        )

    return make_validator


async def test_no_rule_always_passes(validator_with_mocks) -> None:
    """When no rule exists for event_type, validate_can_emit does not raise."""
    v = validator_with_mocks(rule=None, events=[])
    await v.validate_can_emit("t1", "sub1", "updated")
    await v.validate_can_emit("t1", "sub1", "created")


async def test_required_prior_satisfied_passes(validator_with_mocks) -> None:
    """When required_prior_event_types are present in stream, validation passes."""
    rule = _mock_rule("updated", ["created"])
    events = [
        _MockEvent("created", {"x": 1}, datetime(2025, 1, 1, tzinfo=timezone.utc)),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    await v.validate_can_emit("t1", "sub1", "updated")


async def test_required_prior_missing_raises(validator_with_mocks) -> None:
    """When a required prior event type is missing, TransitionValidationException is raised."""
    rule = _mock_rule("updated", ["created"])
    events: list[_MockEvent] = []
    v = validator_with_mocks(rule=rule, events=events)
    with pytest.raises(TransitionValidationException) as exc_info:
        await v.validate_can_emit("t1", "sub1", "updated")
    assert exc_info.value.error_code == "TRANSITION_VIOLATION"
    assert "created" in str(exc_info.value.details["required_prior_event_types"])
    assert exc_info.value.details["event_type"] == "updated"


async def test_payload_condition_satisfied_passes(validator_with_mocks) -> None:
    """When prior_event_payload_conditions match last prior event, validation passes."""
    rule = _mock_rule(
        "status_changed",
        ["created"],
        prior_event_payload_conditions={"created": {"status": "draft"}},
    )
    events = [
        _MockEvent(
            "created",
            {"status": "draft"},
            datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    await v.validate_can_emit("t1", "sub1", "status_changed")


async def test_payload_condition_mismatch_raises(validator_with_mocks) -> None:
    """When payload condition does not match, TransitionValidationException is raised."""
    rule = _mock_rule(
        "status_changed",
        ["created"],
        prior_event_payload_conditions={"created": {"status": "draft"}},
    )
    events = [
        _MockEvent(
            "created",
            {"status": "published"},
            datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    with pytest.raises(TransitionValidationException) as exc_info:
        await v.validate_can_emit("t1", "sub1", "status_changed")
    assert exc_info.value.details.get("reason") == "payload_condition_failed"
    assert exc_info.value.details.get("expected_payload") == {"status": "draft"}


async def test_max_occurrences_per_stream_not_exceeded_passes(validator_with_mocks) -> None:
    """When event_type count is below max_occurrences_per_stream, validation passes."""
    rule = _mock_rule("reminder_sent", ["created"], max_occurrences_per_stream=2)
    events = [
        _MockEvent("created", {}, datetime(2025, 1, 1, tzinfo=timezone.utc)),
        _MockEvent("reminder_sent", {}, datetime(2025, 1, 2, tzinfo=timezone.utc)),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    await v.validate_can_emit("t1", "sub1", "reminder_sent")


async def test_max_occurrences_per_stream_exceeded_raises(validator_with_mocks) -> None:
    """When event_type already appears max_occurrences_per_stream times, validation raises."""
    rule = _mock_rule("reminder_sent", ["created"], max_occurrences_per_stream=1)
    events = [
        _MockEvent("created", {}, datetime(2025, 1, 1, tzinfo=timezone.utc)),
        _MockEvent("reminder_sent", {}, datetime(2025, 1, 2, tzinfo=timezone.utc)),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    with pytest.raises(TransitionValidationException) as exc_info:
        await v.validate_can_emit("t1", "sub1", "reminder_sent")
    assert exc_info.value.details.get("reason") == "max_occurrences_per_stream"
    assert exc_info.value.details.get("max") == 1


async def test_fresh_prior_required_when_current_exists_passes(validator_with_mocks) -> None:
    """When fresh_prior_event_type is after last current event_type, validation passes."""
    rule = _mock_rule(
        "reminder_sent",
        ["created"],
        fresh_prior_event_type="consent_given",
    )
    events = [
        _MockEvent("created", {}, datetime(2025, 1, 1, tzinfo=timezone.utc)),
        _MockEvent("reminder_sent", {}, datetime(2025, 1, 2, tzinfo=timezone.utc)),
        _MockEvent("consent_given", {}, datetime(2025, 1, 3, tzinfo=timezone.utc)),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    await v.validate_can_emit("t1", "sub1", "reminder_sent")


async def test_fresh_prior_required_but_missing_raises(validator_with_mocks) -> None:
    """When fresh_prior_event_type is required but last current is after last fresh, raises."""
    rule = _mock_rule(
        "reminder_sent",
        ["created"],
        fresh_prior_event_type="consent_given",
    )
    events = [
        _MockEvent("created", {}, datetime(2025, 1, 1, tzinfo=timezone.utc)),
        _MockEvent("consent_given", {}, datetime(2025, 1, 2, tzinfo=timezone.utc)),
        _MockEvent("reminder_sent", {}, datetime(2025, 1, 3, tzinfo=timezone.utc)),
    ]
    v = validator_with_mocks(rule=rule, events=events)
    with pytest.raises(TransitionValidationException) as exc_info:
        await v.validate_can_emit("t1", "sub1", "reminder_sent")
    assert exc_info.value.details.get("reason") == "fresh_prior_required"
    assert exc_info.value.details.get("fresh_prior_event_type") == "consent_given"
