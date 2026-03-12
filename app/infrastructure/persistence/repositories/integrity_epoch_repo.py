"""Integrity epoch repository implementation."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.integrity import OpenEpochAssignment
from app.application.integrity_config import INTEGRITY_PROFILE_CONFIG
from app.domain.enums import IntegrityEpochStatus, IntegrityProfile
from app.infrastructure.persistence.models import IntegrityEpoch
from app.infrastructure.persistence.repositories.base import BaseRepository


def _epoch_to_assignment(e: IntegrityEpoch) -> OpenEpochAssignment:
    """Map ORM epoch to OpenEpochAssignment."""
    return OpenEpochAssignment(
        epoch_id=e.id,
        profile_snapshot=e.profile_snapshot,
        event_count=e.event_count,
    )


class IntegrityEpochRepository(BaseRepository[IntegrityEpoch]):
    """Repository for integrity epochs."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, IntegrityEpoch)

    async def get_open_epoch_for_update(
        self,
        tenant_id: str,
        subject_id: str,
    ) -> OpenEpochAssignment | None:
        """Return the open epoch for (tenant, subject) with a row lock, or None."""
        result = await self.db.execute(
            select(IntegrityEpoch)
            .where(
                IntegrityEpoch.tenant_id == tenant_id,
                IntegrityEpoch.subject_id == subject_id,
                IntegrityEpoch.status == IntegrityEpochStatus.OPEN,
            )
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        return _epoch_to_assignment(row) if row else None

    async def get_latest_sealed_terminal_hash(
        self,
        tenant_id: str,
        subject_id: str,
    ) -> str | None:
        """Return terminal_hash of the latest sealed epoch, or None."""
        result = await self.db.execute(
            select(IntegrityEpoch.terminal_hash)
            .where(
                IntegrityEpoch.tenant_id == tenant_id,
                IntegrityEpoch.subject_id == subject_id,
                IntegrityEpoch.status == IntegrityEpochStatus.SEALED,
            )
            .order_by(desc(IntegrityEpoch.epoch_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_epoch_number(
        self,
        tenant_id: str,
        subject_id: str,
    ) -> int:
        """Return the next epoch number (max+1 or 0) for (tenant, subject)."""
        result = await self.db.execute(
            select(func.coalesce(func.max(IntegrityEpoch.epoch_number), -1) + 1).where(
                IntegrityEpoch.tenant_id == tenant_id,
                IntegrityEpoch.subject_id == subject_id,
            )
        )
        value = result.scalar() or 0
        return int(value)

    async def create_epoch(
        self,
        tenant_id: str,
        subject_id: str,
        epoch_number: int,
        genesis_hash: str,
        profile_snapshot: str,
    ) -> OpenEpochAssignment:
        """Create a new open epoch; first_event_seq is set when the first event is appended."""
        epoch = IntegrityEpoch(
            tenant_id=tenant_id,
            subject_id=subject_id,
            epoch_number=epoch_number,
            genesis_hash=genesis_hash,
            first_event_seq=None,
            last_event_seq=None,
            event_count=0,
            opened_at=datetime.now(timezone.utc),
            profile_snapshot=profile_snapshot,
            status=IntegrityEpochStatus.OPEN,
        )
        created = await self.create(epoch)
        return _epoch_to_assignment(created)

    async def get_sealable_epochs(self, limit: int = 50) -> list[IntegrityEpoch]:
        """Return OPEN epochs that are due for sealing (time or event count). FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)
        due_conditions = []
        for profile in IntegrityProfile:
            config = INTEGRITY_PROFILE_CONFIG.get(profile)
            if not config:
                continue
            cutoff = now - timedelta(seconds=config.seal_seconds)
            due_conditions.append(
                and_(
                    IntegrityEpoch.profile_snapshot == profile.value,
                    or_(
                        IntegrityEpoch.opened_at < cutoff,
                        IntegrityEpoch.event_count >= config.seal_event_count,
                    ),
                )
            )
        if not due_conditions:
            return []
        result = await self.db.execute(
            select(IntegrityEpoch)
            .where(
                IntegrityEpoch.status == IntegrityEpochStatus.OPEN,
                or_(*due_conditions),
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def seal_epoch(
        self,
        epoch_id: str,
        terminal_hash: str,
        *,
        tsa_anchor_id: str | None = None,
        merkle_root: str | None = None,
    ) -> None:
        """Mark epoch as SEALED; set terminal_hash, sealed_at, optional tsa_anchor_id and merkle_root."""
        values: dict[str, object] = {
            "status": IntegrityEpochStatus.SEALED,
            "terminal_hash": terminal_hash,
            "sealed_at": datetime.now(timezone.utc),
        }
        if tsa_anchor_id is not None:
            values["tsa_anchor_id"] = tsa_anchor_id
        if merkle_root is not None:
            values["merkle_root"] = merkle_root
        await self.db.execute(
            update(IntegrityEpoch).where(IntegrityEpoch.id == epoch_id).values(**values)
        )

    async def increment_epoch_event(
        self,
        epoch_id: str,
        last_event_seq: int,
        *,
        is_first: bool = False,
    ) -> None:
        """Increment event_count and set last_event_seq; if is_first, set first_event_seq."""
        if is_first:
            stmt = (
                update(IntegrityEpoch)
                .where(IntegrityEpoch.id == epoch_id)
                .values(
                    first_event_seq=last_event_seq,
                    last_event_seq=last_event_seq,
                    event_count=1,
                )
            )
        else:
            stmt = (
                update(IntegrityEpoch)
                .where(IntegrityEpoch.id == epoch_id)
                .values(
                    event_count=IntegrityEpoch.event_count + 1,
                    last_event_seq=last_event_seq,
                )
            )
        await self.db.execute(stmt)

    async def mark_epoch_failed(self, epoch_id: str) -> None:
        """Mark epoch as FAILED so it is skipped by get_sealable_epochs."""
        await self.db.execute(
            update(IntegrityEpoch)
            .where(IntegrityEpoch.id == epoch_id)
            .values(status=IntegrityEpochStatus.FAILED)
        )

