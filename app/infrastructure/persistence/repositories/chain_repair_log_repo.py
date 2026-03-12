"""Repository for chain_repair_log records."""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ChainRepairStatus
from app.infrastructure.persistence.models import ChainRepairLog
from app.infrastructure.persistence.repositories.base import BaseRepository


class ChainRepairLogRepository(BaseRepository[ChainRepairLog]):
    """Persistence operations for ChainRepairLog."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ChainRepairLog)

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
    ) -> ChainRepairLog:
        """Insert a new chain_repair_log row and return it."""
        now = datetime.now(timezone.utc)
        obj = ChainRepairLog(
            tenant_id=tenant_id,
            epoch_id=epoch_id,
            break_detected_at=now,
            break_at_event_seq=break_at_event_seq,
            break_reason=break_reason,
            repair_initiated_by=repair_initiated_by,
            approval_required=approval_required,
            repair_reference=repair_reference,
            repair_status="PENDING_APPROVAL" if approval_required else "APPROVED",
        )
        created = await self.create(obj)
        return created

    async def get_by_id(self, repair_id: str) -> ChainRepairLog | None:
        result = await self.db.execute(
            select(ChainRepairLog).where(ChainRepairLog.id == repair_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        repair_id: str,
        *,
        status: ChainRepairStatus,
        repair_approved_by: str | None = None,
        new_epoch_id: str | None = None,
    ) -> None:
        """Update repair_status and optional approver/new_epoch_id."""
        values: dict[str, object] = {"repair_status": status.value}
        if repair_approved_by is not None:
            values["repair_approved_by"] = repair_approved_by
        if new_epoch_id is not None:
            values["new_epoch_id"] = new_epoch_id
        stmt = update(ChainRepairLog).where(ChainRepairLog.id == repair_id).values(**values)
        await self.db.execute(stmt)

