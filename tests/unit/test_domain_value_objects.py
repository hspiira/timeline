"""Tests for domain value objects (TenantCode, SubjectType, EventType, Hash, EventChain)."""

import pytest

from app.domain.value_objects.core import (
    EventChain,
    EventType,
    Hash,
    SubjectType,
    TenantCode,
)


class TestTenantCode:
    """TenantCode: 3-15 chars, lowercase alphanumeric with optional hyphens."""

    def test_valid_codes(self) -> None:
        TenantCode("acme")
        TenantCode("acme-corp")
        TenantCode("a12")
        TenantCode("a" * 15)

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            TenantCode("")

    def test_too_short_rejected(self) -> None:
        with pytest.raises(ValueError, match="3-15"):
            TenantCode("ab")

    def test_too_long_rejected(self) -> None:
        with pytest.raises(ValueError, match="3-15"):
            TenantCode("a" * 16)

    def test_invalid_format_rejected(self) -> None:
        with pytest.raises(ValueError, match="lowercase"):
            TenantCode("ACME")
        with pytest.raises(ValueError, match="lowercase"):
            TenantCode("acme_corp")
        with pytest.raises(ValueError, match="lowercase"):
            TenantCode("acme corp")


class TestSubjectType:
    """SubjectType: non-empty, max 150 chars, lowercase alphanumeric with optional underscores."""

    def test_valid_types(self) -> None:
        SubjectType("client")
        SubjectType("system_audit")
        SubjectType("a" * 150)

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            SubjectType("")

    def test_too_long_rejected(self) -> None:
        with pytest.raises(ValueError, match="150"):
            SubjectType("a" * 151)

    def test_invalid_format_rejected(self) -> None:
        with pytest.raises(ValueError, match="underscores"):
            SubjectType("Client")
        with pytest.raises(ValueError, match="underscores"):
            SubjectType("system-audit")


class TestEventType:
    """EventType: non-empty string; custom types allowed."""

    def test_valid_standard_types(self) -> None:
        for t in ("created", "updated", "deleted", "status_changed"):
            EventType(t)

    def test_custom_type_allowed(self) -> None:
        EventType("custom_event")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            EventType("")


class TestHash:
    """Hash: 64 (SHA-256) or 128 (SHA-512) hex chars."""

    def test_valid_sha256(self) -> None:
        h = Hash("a" * 64)
        assert h.value == "a" * 64

    def test_valid_sha512(self) -> None:
        h = Hash("b" * 128)
        assert h.value == "b" * 128

    def test_normalized_to_lowercase(self) -> None:
        h = Hash("A" * 64)
        assert h.value == "a" * 64

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            Hash("")

    def test_wrong_length_rejected(self) -> None:
        with pytest.raises(ValueError, match="64|128"):
            Hash("a" * 32)
        with pytest.raises(ValueError, match="64|128"):
            Hash("a" * 65)

    def test_non_hex_rejected(self) -> None:
        with pytest.raises(ValueError, match="hex"):
            Hash("g" + "a" * 63)


class TestEventChain:
    """EventChain: current_hash and optional previous_hash; current != previous."""

    def test_genesis_event(self) -> None:
        chain = EventChain(current_hash=Hash("a" * 64), previous_hash=None)
        assert chain.is_genesis_event() is True

    def test_chained_event(self) -> None:
        chain = EventChain(
            current_hash=Hash("b" * 64),
            previous_hash=Hash("a" * 64),
        )
        assert chain.is_genesis_event() is False

    def test_self_reference_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot reference itself"):
            EventChain(
                current_hash=Hash("a" * 64),
                previous_hash=Hash("a" * 64),
            )
