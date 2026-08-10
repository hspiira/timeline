"""Chain repair service (detect and flag, initiate, approve, complete repair)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from app.application.interfaces.services import IHashService
from app.domain.enums import (
    ChainRepairStatus,
    EventIntegrityStatus,
    IntegrityProfile,
)
from app.shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IEventRepository,
        IEpochRepository,
    )

logger = logging.getLogger(__name__)

CHAIN_REPAIR_EVENT_TYPE = "CHAIN_REPAIR"


class IChainRepairLogRepository(Protocol):
    """Protocol for chain_repair_log persistence (initiate, approve)."""

    async def create_log(
        self,
        *,
        tenant_id: str,
        epoch_id: str,
        break_at_event_seq: int,
        break_reason: str,
        repair_initiated_by: str,
        approval_required: bool,
        repair_reference: str | None,
    ) -> Any: ...
    async def get_by_id(self, repair_id: str) -> Any: ...
    async def update_status(
        self,
        repair_id: str,
        *,
        status: ChainRepairStatus,
        repair_approved_by: str | None = None,
        new_epoch_id: str | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class ChainBreakInfo:
    """Information about the first detected chain break for a subject."""

    event_id: str
    break_at_event_seq: int
    epoch_id: str | None
    subject_id: str


@dataclass(frozen=True)
class ChainRepairRecord:
    """Lightweight view of a chain repair log entry."""

    id: str
    tenant_id: str
    epoch_id: str
    break_at_event_seq: int
    break_reason: str
    repair_status: ChainRepairStatus
    repair_initiated_by: str
    repair_approved_by: str | None
    approval_required: bool
    repair_reference: str | None
    repair_completed_at: datetime | None
    new_epoch_id: str | None


class ChainRepairService:
    """Implements chain repair workflow as described in chain_integrity_architecture.md §4.5."""

    def __init__(
        self,
        *,
        event_repo: IEventRepository,
        epoch_repo: IEpochRepository,
        repair_repo: IChainRepairLogRepository,
        hash_service: IHashService,
    ) -> None:
        self._event_repo = event_repo
        self._epoch_repo = epoch_repo
        self._repair_repo = repair_repo
        self._hash_service = hash_service

    async def detect_and_flag(
        self, tenant_id: str, subject_id: str
    ) -> ChainBreakInfo | None:
        """Walk events, recompute chain, and flag the first break.

        On mismatch:
          - Set event.integrity_status = 'CHAIN_BREAK'
          - Set epoch.status = 'BROKEN'

        Returns:
            ChainBreakInfo for the first break, or None if the chain is clean.
        """
        batch_size = 500
        last_hash: str | None = None
        after_event_id: str | None = None

        while True:
            events = await self._event_repo.get_events_chronological(
                subject_id=subject_id,
                tenant_id=tenant_id,
                as_of=None,
                after_event_id=after_event_id,
                workflow_instance_id=None,
                limit=batch_size,
            )
            if not events:
                return None

            for ev in events:
                if last_hash is not None and ev.previous_hash != last_hash:
                    logger.warning(
                        "detect_and_flag: chain break detected at subject_id=%s, event_seq=%s",
                        subject_id,
                        ev.event_seq,
                    )
                    await self._event_repo.mark_event_integrity_status(
                        ev.id, EventIntegrityStatus.CHAIN_BREAK.value
                    )
                    epoch_id = ev.epoch_id
                    if epoch_id is not None:
                        await self._epoch_repo.mark_epoch_broken(epoch_id)
                    return ChainBreakInfo(
                        event_id=ev.id,
                        break_at_event_seq=ev.event_seq or 0,
                        epoch_id=epoch_id,
                        subject_id=subject_id,
                    )
                last_hash = ev.hash

            if len(events) < batch_size:
                return None
            after_event_id = events[-1].id

    async def initiate_repair(
        self,
        *,
        tenant_id: str,
        epoch_id: str,
        break_at_event_seq: int,
        break_reason: str,
        initiated_by: str,
        profile: IntegrityProfile,
        repair_reference: str | None = None,
    ) -> ChainRepairRecord:
        """Initiate a chain repair request and persist it to chain_repair_log."""
        if profile is IntegrityProfile.LEGAL_GRADE and not repair_reference:
            raise ValueError("repair_reference required for LEGAL_GRADE")

        approval_required = profile in (
            IntegrityProfile.COMPLIANCE,
            IntegrityProfile.LEGAL_GRADE,
        )

        row = await self._repair_repo.create_log(
            tenant_id=tenant_id,
            epoch_id=epoch_id,
            break_at_event_seq=break_at_event_seq,
            break_reason=break_reason,
            repair_initiated_by=initiated_by,
            approval_required=approval_required,
            repair_reference=repair_reference,
        )
        return self._to_record(row)

    async def approve_repair(
        self,
        repair_id: str,
        approver_id: str,
        tenant_id: str,
    ) -> ChainRepairRecord:
        """Approve a pending repair using four-eyes rule (approver ≠ initiator) and return updated record.

        Tenant ownership is enforced before mutation to prevent cross-tenant approvals.
        """
        repair = await self._repair_repo.get_by_id(repair_id)
        if not repair or repair.tenant_id != tenant_id:
            raise ValueError(f"Repair id {repair_id!r} not found")
        if not repair.approval_required:
            # Nothing to do; implicitly approved.
            return self._to_record(repair)
        if repair.repair_initiated_by == approver_id:
            raise PermissionError("Approver must differ from initiator (four-eyes)")
        await self._repair_repo.update_status(
            repair_id,
            status=ChainRepairStatus.APPROVED,
            repair_approved_by=approver_id,
        )
        # Reload so caller sees updated status/approver.
        updated = await self._repair_repo.get_by_id(repair_id)
        if not updated:
            raise ValueError(f"Repair id {repair_id!r} not found after approve")
        return self._to_record(updated)

    async def complete_repair(self, repair_id: str) -> ChainRepairRecord:
        """Re-hash from break, append CHAIN_REPAIR event, open new epoch, set events to REPAIRED."""
        repair = await self._repair_repo.get_by_id(repair_id)
        if not repair:
            raise ValueError(f"Repair id {repair_id!r} not found")

        status = ChainRepairStatus(repair.repair_status)
        if repair.approval_required and status is not ChainRepairStatus.APPROVED:
            raise ValueError(
                f"Repair id {repair_id!r} must be approved before completion"
            )
        if status is ChainRepairStatus.COMPLETED:
            return self._to_record(repair)

        # Load epoch to get subject and profile snapshot.
        epoch = await self._epoch_repo.get_by_id(repair.epoch_id)
        if not epoch:
            raise ValueError(f"Epoch id {repair.epoch_id!r} not found for repair")
        subject_id = epoch.subject_id

        # 1. Determine last good hash before the break inside the original epoch.
        if repair.break_at_event_seq <= (epoch.first_event_seq or repair.break_at_event_seq):
            last_good_hash = epoch.genesis_hash
        else:
            last_good_hash = await self._event_repo.get_hash_at_seq(
                repair.tenant_id,
                epoch.id,
                repair.break_at_event_seq - 1,
            ) or epoch.genesis_hash

        # 2. Create a new epoch starting from last_good_hash.
        next_number = await self._epoch_repo.get_next_epoch_number(
            repair.tenant_id, subject_id
        )
        new_epoch = await self._epoch_repo.create_epoch(
            tenant_id=repair.tenant_id,
            subject_id=subject_id,
            epoch_number=next_number,
            genesis_hash=last_good_hash,
            profile_snapshot=epoch.profile_snapshot,
        )

        # 3. Append CHAIN_REPAIR administrative event as first event in new epoch.
        repair_payload: dict[str, Any] = {
            "repair_id": repair_id,
            "break_at_event_seq": repair.break_at_event_seq,
            "break_reason": repair.break_reason,
            "repair_reference": repair.repair_reference,
        }
        event_time = utc_now()
        event_hash = self._hash_service.compute_hash(
            subject_id=subject_id,
            event_type=CHAIN_REPAIR_EVENT_TYPE,
            schema_version=1,
            event_time=event_time,
            payload=repair_payload,
            previous_hash=last_good_hash,
        )
        from app.application.dtos.event import EventCreate  # local import to avoid cycles

        event_create = EventCreate(
            subject_id=subject_id,
            event_type=CHAIN_REPAIR_EVENT_TYPE,
            schema_version=1,
            event_time=event_time,
            payload=repair_payload,
        )
        chain_repair_event = await self._event_repo.create_event(
            tenant_id=repair.tenant_id,
            data=event_create,
            event_hash=event_hash,
            previous_hash=last_good_hash,
            epoch_id=new_epoch.epoch_id,
            integrity_status=EventIntegrityStatus.VALID.value,
            merkle_leaf_hash=None,
        )
        if chain_repair_event.event_seq is None:
            raise ValueError("CHAIN_REPAIR event missing event_seq")
        await self._epoch_repo.increment_epoch_event(
            new_epoch.epoch_id,
            chain_repair_event.event_seq,
            is_first=True,
        )

        # 4. Mark broken events as REPAIRED and original epoch as REPAIRED.
        await self._event_repo.mark_events_repaired_from_seq(
            repair.tenant_id,
            subject_id,
            repair.break_at_event_seq,
        )
        await self._epoch_repo.mark_epoch_repaired(repair.epoch_id)

        # 5. Update repair log status to COMPLETED and point to new epoch.
        await self._repair_repo.update_status(
            repair_id,
            status=ChainRepairStatus.COMPLETED,
            new_epoch_id=new_epoch.epoch_id,
        )
        updated = await self._repair_repo.get_by_id(repair_id)
        if not updated:
            raise ValueError(f"Repair id {repair_id!r} not found after completion")
        return self._to_record(updated)

    async def get_repair(self, repair_id: str) -> ChainRepairRecord:
        """Return a single repair record by id."""
        row = await self._repair_repo.get_by_id(repair_id)
        if not row:
            raise ValueError(f"Repair id {repair_id!r} not found")
        return self._to_record(row)

    @staticmethod
    def _to_record(row: Any) -> ChainRepairRecord:
        return ChainRepairRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            epoch_id=row.epoch_id,
            break_at_event_seq=row.break_at_event_seq,
            break_reason=row.break_reason,
            repair_status=ChainRepairStatus(row.repair_status),
            repair_initiated_by=row.repair_initiated_by,
            repair_approved_by=row.repair_approved_by,
            approval_required=row.approval_required,
            repair_reference=row.repair_reference,
            repair_completed_at=row.repair_completed_at,
            new_epoch_id=row.new_epoch_id,
        )

