"""Chain repair service (detect and flag, initiate, approve, complete repair)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from app.domain.enums import IntegrityProfile

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IEventRepository,
        IEpochRepository,
    )

logger = logging.getLogger(__name__)


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
        status: str,
        repair_approved_by: str | None = None,
        new_epoch_id: str | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class ChainRepairRecord:
    """Lightweight view of a chain repair log entry."""

    id: str
    tenant_id: str
    epoch_id: str
    break_at_event_seq: int
    break_reason: str
    repair_status: str
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
    ) -> None:
        self._event_repo = event_repo
        self._epoch_repo = epoch_repo
        self._repair_repo = repair_repo

    async def detect_and_flag(self, tenant_id: str, subject_id: str) -> None:
        """Walk events, recompute chain, and flag the first break.

        On mismatch:
          - Set event.integrity_status = 'CHAIN_BREAK'
          - Set epoch.status = 'BROKEN'

        Raises:
            NotImplementedError: Storage-level flagging not yet implemented.
        """
        events = await self._event_repo.get_events_chronological(
            subject_id=subject_id,
            tenant_id=tenant_id,
            as_of=None,
            after_event_id=None,
            workflow_instance_id=None,
            limit=100_000,
        )
        if not events:
            return
        last_hash: str | None = None
        for ev in events:
            if last_hash is not None and ev.previous_hash != last_hash:
                logger.warning(
                    "detect_and_flag: chain break detected at subject_id=%s but flagging not implemented",
                    subject_id,
                )
                raise NotImplementedError(
                    "detect_and_flag: setting integrity_status='CHAIN_BREAK' and epoch status='BROKEN' not yet implemented"
                )
            last_hash = ev.hash

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

    async def approve_repair(self, repair_id: str, approver_id: str) -> None:
        """Approve a pending repair using four-eyes rule (approver ≠ initiator)."""
        repair = await self._repair_repo.get_by_id(repair_id)
        if not repair:
            raise ValueError(f"Repair id {repair_id!r} not found")
        if not repair.approval_required:
            # Nothing to do; implicitly approved.
            return
        if repair.repair_initiated_by == approver_id:
            raise PermissionError("Approver must differ from initiator (four-eyes)")
        await self._repair_repo.update_status(
            repair_id,
            status="APPROVED",
            repair_approved_by=approver_id,
        )

    async def complete_repair(self, repair_id: str) -> None:
        """Re-hash from break, append CHAIN_REPAIR event, open new epoch, set events to REPAIRED.

        Raises:
            NotImplementedError: Full repair algorithm not yet implemented.
        """
        repair = await self._repair_repo.get_by_id(repair_id)
        if not repair:
            raise ValueError(f"Repair id {repair_id!r} not found")
        logger.warning(
            "complete_repair(repair_id=%s): not yet implemented; not writing to repair log",
            repair_id,
        )
        raise NotImplementedError(
            "complete_repair: re-hash from break, CHAIN_REPAIR event, and new epoch not yet implemented"
        )

    @staticmethod
    def _to_record(row: Any) -> ChainRepairRecord:
        return ChainRepairRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            epoch_id=row.epoch_id,
            break_at_event_seq=row.break_at_event_seq,
            break_reason=row.break_reason,
            repair_status=row.repair_status,
            repair_initiated_by=row.repair_initiated_by,
            repair_approved_by=row.repair_approved_by,
            approval_required=row.approval_required,
            repair_reference=row.repair_reference,
            repair_completed_at=row.repair_completed_at,
            new_epoch_id=row.new_epoch_id,
        )

