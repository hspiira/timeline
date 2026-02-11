"""Chain verification service: recompute hashes and validate previous_hash links."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from app.application.dtos.event import EventResult
from app.application.interfaces.repositories import IEventRepository
from app.application.interfaces.services import IHashService
from app.shared.utils.datetime import utc_now


@dataclass(kw_only=True)
class VerificationResult:
    """Result of verifying a single event."""

    event_id: str
    event_type: str
    event_time: datetime
    sequence: int
    is_valid: bool
    error_type: str | None = None
    error_message: str | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None
    previous_hash: str | None = None


@dataclass(kw_only=True)
class ChainVerificationResult:
    """Result of verifying a subject or tenant chain."""

    subject_id: str | None
    tenant_id: str
    total_events: int
    valid_events: int
    invalid_events: int
    is_chain_valid: bool
    verified_at: datetime
    event_results: list[VerificationResult] = field(default_factory=list)


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
        """Verify event chain for one subject. Events sorted by event_time (oldest first)."""
        # Fetch ALL events for the subject so chain verification is complete (no silent truncation).
        all_events: list[EventResult] = []
        batch_size = 500
        offset = 0
        while True:
            batch = await self.event_repo.get_by_subject(
                subject_id, tenant_id, skip=offset, limit=batch_size
            )
            all_events.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
        events = sorted(all_events, key=lambda e: e.event_time)

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

        results, valid, invalid = self._verify_events_chain(events)
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
        self, tenant_id: str
    ) -> ChainVerificationResult:
        """Verify all event chains for a tenant (grouped by subject).

        Fetches all events in batches so verification is complete with no silent truncation.
        """
        all_events: list[EventResult] = []
        batch_size = 500
        offset = 0
        while True:
            batch = await self.event_repo.get_by_tenant(
                tenant_id, skip=offset, limit=batch_size
            )
            all_events.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
        events = all_events
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

        by_subject: dict[str, list[EventResult]] = {}
        for event in events:
            sid = event.subject_id
            if sid not in by_subject:
                by_subject[sid] = []
            by_subject[sid].append(event)
        for sid in by_subject:
            by_subject[sid] = sorted(
                by_subject[sid],
                key=lambda e: e.event_time,
            )

        results = []
        valid, invalid = 0, 0
        for subject_events in by_subject.values():
            r_list, v, inv = self._verify_events_chain(subject_events)
            results.extend(r_list)
            valid += v
            invalid += inv

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

    def _verify_events_chain(
        self, events: list[EventResult]
    ) -> tuple[list[VerificationResult], int, int]:
        """Verify a chain of events (sorted by event_time). Returns (results, valid_count, invalid_count)."""
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
        return results, valid, invalid

    def _verify_event(
        self,
        event: EventResult,
        previous_event: EventResult | None,
        sequence: int,
    ) -> VerificationResult:
        """Verify one event: hash match and previous_hash link."""
        subject_id = event.subject_id
        event_type = event.event_type
        event_time = event.event_time
        payload = event.payload
        schema_version = event.schema_version
        previous_hash = event.previous_hash
        event_hash = event.hash
        event_id = event.id

        def result(
            *,
            is_valid: bool,
            error_type: str | None = None,
            error_message: str | None = None,
            expected_hash: str | None = None,
            actual_hash: str | None = None,
        ) -> VerificationResult:
            return VerificationResult(
                event_id=event_id,
                event_type=event_type,
                event_time=event_time,
                sequence=sequence,
                is_valid=is_valid,
                error_type=error_type,
                error_message=error_message,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                previous_hash=previous_hash,
            )

        computed = self.hash_service.compute_hash(
            subject_id=subject_id,
            event_type=event_type,
            schema_version=schema_version,
            event_time=event_time,
            payload=payload,
            previous_hash=previous_hash,
        )

        if computed != event_hash:
            return result(
                is_valid=False,
                error_type="HASH_MISMATCH",
                error_message="Event hash does not match recomputed hash",
                expected_hash=computed,
                actual_hash=event_hash,
            )

        if sequence == 0:
            if previous_hash is not None:
                return result(
                    is_valid=False,
                    error_type="GENESIS_ERROR",
                    error_message="Genesis event should have null previous_hash",
                )
        else:
            if previous_event is None:
                return result(
                    is_valid=False,
                    error_type="MISSING_PREVIOUS",
                    error_message="Previous event not found",
                )
            prev_hash = previous_event.hash
            if previous_hash != prev_hash:
                return result(
                    is_valid=False,
                    error_type="CHAIN_BREAK",
                    error_message="previous_hash does not match previous event",
                    expected_hash=prev_hash,
                    actual_hash=previous_hash,
                )

        return result(
            is_valid=True,
            expected_hash=event_hash,
            actual_hash=event_hash,
        )
