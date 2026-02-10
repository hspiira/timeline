"""Chain verification service: recompute hashes and validate previous_hash links."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.interfaces.repositories import IEventRepository
from app.application.interfaces.services import IHashService
from app.shared.utils.datetime import utc_now


class VerificationResult:
    """Result of verifying a single event."""

    def __init__(
        self,
        event_id: str,
        event_type: str,
        event_time: datetime,
        sequence: int,
        is_valid: bool,
        error_type: str | None = None,
        error_message: str | None = None,
        expected_hash: str | None = None,
        actual_hash: str | None = None,
        previous_hash: str | None = None,
    ) -> None:
        self.event_id = event_id
        self.event_type = event_type
        self.event_time = event_time
        self.sequence = sequence
        self.is_valid = is_valid
        self.error_type = error_type
        self.error_message = error_message
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.previous_hash = previous_hash


class ChainVerificationResult:
    """Result of verifying a subject or tenant chain."""

    def __init__(
        self,
        subject_id: str | None,
        tenant_id: str,
        total_events: int,
        valid_events: int,
        invalid_events: int,
        is_chain_valid: bool,
        verified_at: datetime,
        event_results: list[VerificationResult],
    ) -> None:
        self.subject_id = subject_id
        self.tenant_id = tenant_id
        self.total_events = total_events
        self.valid_events = valid_events
        self.invalid_events = invalid_events
        self.is_chain_valid = is_chain_valid
        self.verified_at = verified_at
        self.event_results = event_results


class VerificationService:
    """Verifies cryptographic integrity of event chains (hash + previous_hash links)."""

    def __init__(
        self,
        event_repo: IEventRepository,
        hash_service: IHashService,
    ) -> None:
        self.event_repo = event_repo
        self.hash_service = hash_service

    async def verify_subject_chain(
        self, subject_id: str, tenant_id: str
    ) -> ChainVerificationResult:
        """Verify event chain for one subject. Events sorted by created_at (oldest first)."""
        events = await self.event_repo.get_by_subject(subject_id, tenant_id)
        events = sorted(events, key=lambda e: getattr(e, "created_at"))

        if not events:
            return ChainVerificationResult(
                subject_id=subject_id,
                tenant_id=tenant_id,
                total_events=0,
                valid_events=0,
                invalid_events=0,
                is_chain_valid=True,
                verified_at=utc_now(),
                event_results=[],
            )

        results: list[VerificationResult] = []
        valid, invalid = 0, 0
        for i, event in enumerate(events):
            prev = events[i - 1] if i > 0 else None
            r = self._verify_event(event, prev, i)
            results.append(r)
            if r.is_valid:
                valid += 1
            else:
                invalid += 1

        return ChainVerificationResult(
            subject_id=subject_id,
            tenant_id=tenant_id,
            total_events=len(events),
            valid_events=valid,
            invalid_events=invalid,
            is_chain_valid=(invalid == 0),
            verified_at=utc_now(),
            event_results=results,
        )

    async def verify_tenant_chains(
        self, tenant_id: str, limit: int | None = None
    ) -> ChainVerificationResult:
        """Verify all event chains for a tenant (grouped by subject)."""
        events = await self.event_repo.get_by_tenant(tenant_id, limit=limit or 100)
        if not events:
            return ChainVerificationResult(
                subject_id=None,
                tenant_id=tenant_id,
                total_events=0,
                valid_events=0,
                invalid_events=0,
                is_chain_valid=True,
                verified_at=utc_now(),
                event_results=[],
            )

        by_subject: dict[str, list[Any]] = {}
        for event in events:
            sid = getattr(event, "subject_id", None)
            if sid not in by_subject:
                by_subject[sid] = []
            by_subject[sid].append(event)
        for sid in by_subject:
            by_subject[sid] = sorted(
                by_subject[sid],
                key=lambda e: getattr(e, "created_at"),
            )

        results = []
        valid, invalid = 0, 0
        for subject_events in by_subject.values():
            for i, event in enumerate(subject_events):
                prev = subject_events[i - 1] if i > 0 else None
                r = self._verify_event(event, prev, i)
                results.append(r)
                if r.is_valid:
                    valid += 1
                else:
                    invalid += 1

        return ChainVerificationResult(
            subject_id=None,
            tenant_id=tenant_id,
            total_events=len(events),
            valid_events=valid,
            invalid_events=invalid,
            is_chain_valid=(invalid == 0),
            verified_at=utc_now(),
            event_results=results,
        )

    def _verify_event(
        self, event: Any, previous_event: Any | None, sequence: int
    ) -> VerificationResult:
        """Verify one event: hash match and previous_hash link."""
        subject_id = getattr(event, "subject_id", "")
        event_type = getattr(event, "event_type", "")
        event_time = getattr(event, "event_time", None)
        payload = getattr(event, "payload", {})
        schema_version = getattr(event, "schema_version", 1)
        previous_hash = getattr(event, "previous_hash", None)
        event_hash = getattr(event, "hash", "")
        event_id = getattr(event, "id", "")

        computed = self.hash_service.compute_hash(
            subject_id=subject_id,
            event_type=event_type,
            schema_version=schema_version,
            event_time=event_time,
            payload=payload,
            previous_hash=previous_hash,
        )

        if computed != event_hash:
            return VerificationResult(
                event_id=event_id,
                event_type=event_type,
                event_time=event_time,
                sequence=sequence,
                is_valid=False,
                error_type="HASH_MISMATCH",
                error_message="Event hash does not match recomputed hash",
                expected_hash=computed,
                actual_hash=event_hash,
                previous_hash=previous_hash,
            )

        if sequence == 0:
            if previous_hash is not None:
                return VerificationResult(
                    event_id=event_id,
                    event_type=event_type,
                    event_time=event_time,
                    sequence=sequence,
                    is_valid=False,
                    error_type="GENESIS_ERROR",
                    error_message="Genesis event should have null previous_hash",
                    previous_hash=previous_hash,
                )
        else:
            if previous_event is None:
                return VerificationResult(
                    event_id=event_id,
                    event_type=event_type,
                    event_time=event_time,
                    sequence=sequence,
                    is_valid=False,
                    error_type="MISSING_PREVIOUS",
                    error_message="Previous event not found",
                    previous_hash=previous_hash,
                )
            prev_hash = getattr(previous_event, "hash", None)
            if previous_hash != prev_hash:
                return VerificationResult(
                    event_id=event_id,
                    event_type=event_type,
                    event_time=event_time,
                    sequence=sequence,
                    is_valid=False,
                    error_type="CHAIN_BREAK",
                    error_message="previous_hash does not match previous event",
                    expected_hash=prev_hash,
                    actual_hash=previous_hash,
                    previous_hash=previous_hash,
                )

        return VerificationResult(
            event_id=event_id,
            event_type=event_type,
            event_time=event_time,
            sequence=sequence,
            is_valid=True,
            expected_hash=event_hash,
            actual_hash=event_hash,
            previous_hash=previous_hash,
        )
