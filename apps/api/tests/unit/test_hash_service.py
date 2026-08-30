"""Tests for HashService (canonical JSON and chain hash)."""

from datetime import datetime, timezone

import pytest

from app.application.services.hash_service import (
    HashService,
    SHA256Algorithm,
    SHA512Algorithm,
)


class TestHashAlgorithm:
    """SHA256 and SHA512 produce deterministic hex hashes."""

    def test_sha256_deterministic(self) -> None:
        a = SHA256Algorithm()
        assert a.hash("hello") == a.hash("hello")
        assert a.hash("hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_sha512_deterministic(self) -> None:
        a = SHA512Algorithm()
        assert a.hash("hello") == a.hash("hello")
        assert len(a.hash("hello")) == 128


class TestHashServiceCanonicalJson:
    """Canonical JSON is deterministic (key order normalized)."""

    def test_sort_keys(self) -> None:
        out = HashService.canonical_json({"b": 1, "a": 2})
        assert out == '{"a":2,"b":1}'

    def test_no_spaces(self) -> None:
        out = HashService.canonical_json({"x": "y"})
        assert " " not in out
        assert out == '{"x":"y"}'


class TestHashServiceComputeHash:
    """Compute hash for event chain; same input gives same hash."""

    def test_deterministic(self) -> None:
        svc = HashService()
        t = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        h1 = svc.compute_hash(
            subject_id="sub1",
            event_type="created",
            schema_version=1,
            event_time=t,
            payload={"name": "test"},
            previous_hash=None,
        )
        h2 = svc.compute_hash(
            subject_id="sub1",
            event_type="created",
            schema_version=1,
            event_time=t,
            payload={"name": "test"},
            previous_hash=None,
        )
        assert h1 == h2
        assert len(h1) == 64

    def test_different_previous_hash_changes_result(self) -> None:
        svc = HashService()
        t = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        h_none = svc.compute_hash(
            subject_id="sub1",
            event_type="created",
            schema_version=1,
            event_time=t,
            payload={},
            previous_hash=None,
        )
        h_prev = svc.compute_hash(
            subject_id="sub1",
            event_type="updated",
            schema_version=1,
            event_time=t,
            payload={},
            previous_hash=h_none,
        )
        assert h_prev != h_none
        assert len(h_prev) == 64

    def test_different_payload_changes_result(self) -> None:
        svc = HashService()
        t = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        h1 = svc.compute_hash(
            subject_id="sub1",
            event_type="created",
            schema_version=1,
            event_time=t,
            payload={"a": 1},
            previous_hash=None,
        )
        h2 = svc.compute_hash(
            subject_id="sub1",
            event_type="created",
            schema_version=1,
            event_time=t,
            payload={"a": 2},
            previous_hash=None,
        )
        assert h1 != h2
