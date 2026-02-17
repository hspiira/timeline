"""Tests for domain entities (EventEntity) and enums (TenantStatus)."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.domain.entities.event import EventEntity
from app.domain.enums import TenantStatus
from app.domain.exceptions import ValidationException
from app.domain.value_objects.core import EventChain, EventType, Hash


class TestTenantStatus:
    """TenantStatus enum values and .values() helper."""

    def test_values_returns_all_status_strings(self) -> None:
        got = TenantStatus.values()
        assert "active" in got
        assert "suspended" in got
        assert "archived" in got
        assert len(got) == 3

    def test_member_values(self) -> None:
        assert TenantStatus.ACTIVE.value == "active"
        assert TenantStatus.SUSPENDED.value == "suspended"
        assert TenantStatus.ARCHIVED.value == "archived"


class TestEventEntityValidateEventTimeAfterPrevious:
    """EventEntity.validate_event_time_after_previous static method."""

    def test_genesis_allowed(self) -> None:
        """Previous None means genesis; any time is allowed."""
        t = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        EventEntity.validate_event_time_after_previous(t, None)

    def test_after_previous_passes(self) -> None:
        prev = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        new = datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
        EventEntity.validate_event_time_after_previous(new, prev)

    def test_same_time_raises(self) -> None:
        t = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationException) as exc_info:
            EventEntity.validate_event_time_after_previous(t, t)
        assert exc_info.value.error_code == "VALIDATION_ERROR"
        assert "event_time" in exc_info.value.details.get("field", "")

    def test_before_previous_raises(self) -> None:
        prev = datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
        new = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationException):
            EventEntity.validate_event_time_after_previous(new, prev)


def _make_valid_chain() -> EventChain:
    return EventChain(
        current_hash=Hash("a" * 64),
        previous_hash=None,
    )


class TestEventEntityValidate:
    """EventEntity validation on construction (validate() and __post_init__)."""

    @patch("app.domain.entities.event.utc_now")
    def test_empty_id_raises(self, mock_utc_now: object) -> None:
        mock_utc_now.return_value = datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationException) as exc_info:
            EventEntity(
                id="",
                tenant_id="t1",
                subject_id="sub1",
                event_type=EventType("created"),
                event_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                payload={"x": 1},
                chain=_make_valid_chain(),
            )
        assert "id" in exc_info.value.details.get("field", "")

    @patch("app.domain.entities.event.utc_now")
    def test_empty_payload_raises(self, mock_utc_now: object) -> None:
        mock_utc_now.return_value = datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationException) as exc_info:
            EventEntity(
                id="ev1",
                tenant_id="t1",
                subject_id="sub1",
                event_type=EventType("created"),
                event_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                payload={},
                chain=_make_valid_chain(),
            )
        assert "payload" in exc_info.value.details.get("field", "")

    @patch("app.domain.entities.event.utc_now")
    def test_future_event_time_raises(self, mock_utc_now: object) -> None:
        mock_utc_now.return_value = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationException) as exc_info:
            EventEntity(
                id="ev1",
                tenant_id="t1",
                subject_id="sub1",
                event_type=EventType("created"),
                event_time=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                payload={"x": 1},
                chain=_make_valid_chain(),
            )
        assert "event_time" in exc_info.value.details.get("field", "")

    @patch("app.domain.entities.event.utc_now")
    def test_valid_entity_constructs(self, mock_utc_now: object) -> None:
        mock_utc_now.return_value = datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        ev = EventEntity(
            id="ev1",
            tenant_id="t1",
            subject_id="sub1",
            event_type=EventType("created"),
            event_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            payload={"name": "test"},
            chain=_make_valid_chain(),
        )
        assert ev.id == "ev1"
        assert ev.is_genesis_event() is True
