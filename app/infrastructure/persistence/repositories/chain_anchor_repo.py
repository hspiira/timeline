"""Chain anchor repository. RFC 3161 TSA receipt storage per tenant chain tip."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import desc

from app.application.dtos.chain_anchor import ChainAnchorResult
from app.domain.enums import ChainAnchorStatus
from app.domain.exceptions import ChainAnchorConflictException
from app.infrastructure.persistence.models.chain_anchor import ChainAnchor
from app.infrastructure.persistence.repositories.base import BaseRepository


def _to_result(a: ChainAnchor) -> ChainAnchorResult:
    """Map ORM to DTO."""
    status = (
        a.status.value
        if isinstance(a.status, ChainAnchorStatus)
        else a.status
    )
    return ChainAnchorResult(
        id=a.id,
        tenant_id=a.tenant_id,
        subject_id=a.subject_id,
        chain_tip_hash=a.chain_tip_hash,
        anchored_at=a.anchored_at,
        tsa_url=a.tsa_url,
        tsa_receipt=a.tsa_receipt,
        tsa_serial=a.tsa_serial,
        status=status,
        error_message=a.error_message,
        created_at=a.created_at,
        event_count=a.event_count,
        subject_tips=a.subject_tips,
    )


class ChainAnchorRepository(BaseRepository[ChainAnchor]):
    """Chain anchor repository. Pending/confirmed/failed lifecycle and list by tenant."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ChainAnchor)

    async def get_by_tenant_and_tip(
        self,
        tenant_id: str,
        chain_tip_hash: str,
        *,
        subject_id: str | None = None,
    ) -> ChainAnchorResult | None:
        """Return anchor for (tenant_id, chain_tip_hash), or (tenant_id, subject_id, chain_tip_hash). subject_id=None for tenant-level."""
        q = select(ChainAnchor).where(
            ChainAnchor.tenant_id == tenant_id,
            ChainAnchor.chain_tip_hash == chain_tip_hash,
        )
        if subject_id is None:
            q = q.where(ChainAnchor.subject_id.is_(None))
        else:
            q = q.where(ChainAnchor.subject_id == subject_id)
        result = await self.db.execute(q)
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def create_pending(
        self,
        tenant_id: str,
        chain_tip_hash: str,
        tsa_url: str,
        *,
        anchored_at: datetime | None = None,
        subject_id: str | None = None,
    ) -> ChainAnchorResult:
        """Create a pending anchor row, or return existing on concurrent duplicate (idempotent).

        subject_id=None for tenant-level. On unique constraint (tenant_id, tip) or
        (tenant_id, subject_id, tip), returns the existing row instead of raising.
        """
        try:
            async with self.db.begin_nested():
                anchor = ChainAnchor(
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    chain_tip_hash=chain_tip_hash,
                    anchored_at=anchored_at,
                    tsa_url=tsa_url,
                    status=ChainAnchorStatus.PENDING,
                )
                created = await self.create(anchor)
                return _to_result(created)
        except IntegrityError:
            existing = await self.get_by_tenant_and_tip(
                tenant_id, chain_tip_hash, subject_id=subject_id
            )
            if existing is not None:
                return existing
            raise ChainAnchorConflictException(
                "Anchor already exists for this chain tip but could not be loaded.",
                details={"tenant_id": tenant_id, "chain_tip_hash": chain_tip_hash},
            )

    async def update_confirmed(
        self, anchor_id: str, tsa_receipt: bytes, tsa_serial: str | None
    ) -> ChainAnchorResult | None:
        """Mark anchor as confirmed and store receipt; return updated result or None.

        Updates when status is pending or failed so a valid TSA receipt is not dropped
        if a concurrent update_failed() raced in (stale-pending retry).
        """
        result = await self.db.execute(
            update(ChainAnchor)
            .where(
                ChainAnchor.id == anchor_id,
                ChainAnchor.status.in_(
                    (ChainAnchorStatus.PENDING, ChainAnchorStatus.FAILED)
                ),
            )
            .values(
                status=ChainAnchorStatus.CONFIRMED,
                tsa_receipt=tsa_receipt,
                tsa_serial=tsa_serial,
                error_message=None,
            )
        )
        if result.rowcount != 1:
            return None
        await self.db.flush()
        row_result = await self.db.execute(select(ChainAnchor).where(ChainAnchor.id == anchor_id))
        row = row_result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def update_failed(self, anchor_id: str, error_message: str) -> ChainAnchorResult | None:
        """Mark anchor as failed; return updated result or None. Only updates when status is not confirmed."""
        result = await self.db.execute(
            update(ChainAnchor)
            .where(
                ChainAnchor.id == anchor_id,
                ChainAnchor.status != ChainAnchorStatus.CONFIRMED,
            )
            .values(status=ChainAnchorStatus.FAILED, error_message=error_message)
        )
        if result.rowcount != 1:
            return None
        await self.db.flush()
        row_result = await self.db.execute(select(ChainAnchor).where(ChainAnchor.id == anchor_id))
        row = row_result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def update_to_pending(self, anchor_id: str) -> ChainAnchorResult | None:
        """Set status to pending and clear error_message (for retry after failed). Only updates when status is failed."""
        result = await self.db.execute(
            update(ChainAnchor)
            .where(
                ChainAnchor.id == anchor_id,
                ChainAnchor.status == ChainAnchorStatus.FAILED,
            )
            .values(status=ChainAnchorStatus.PENDING, error_message=None)
        )
        if result.rowcount != 1:
            return None
        await self.db.flush()
        row_result = await self.db.execute(select(ChainAnchor).where(ChainAnchor.id == anchor_id))
        row = row_result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def list_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        *,
        tenant_level_only: bool = True,
    ) -> list[ChainAnchorResult]:
        """List anchors for tenant, newest first. tenant_level_only=True (default) returns only tenant-level (subject_id IS NULL)."""
        q = select(ChainAnchor).where(ChainAnchor.tenant_id == tenant_id)
        if tenant_level_only:
            q = q.where(ChainAnchor.subject_id.is_(None))
        q = q.order_by(
            desc(ChainAnchor.anchored_at),
            desc(ChainAnchor.created_at),
            desc(ChainAnchor.id),
        ).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return [_to_result(r) for r in result.scalars().all()]

    async def get_latest_confirmed(
        self,
        tenant_id: str,
        *,
        tenant_level_only: bool = True,
    ) -> ChainAnchorResult | None:
        """Return the most recent confirmed anchor for tenant, or None. tenant_level_only=True (default) returns only tenant-level (subject_id IS NULL)."""
        q = select(ChainAnchor).where(
            ChainAnchor.tenant_id == tenant_id,
            ChainAnchor.status == ChainAnchorStatus.CONFIRMED,
        )
        if tenant_level_only:
            q = q.where(ChainAnchor.subject_id.is_(None))
        result = await self.db.execute(
            q.order_by(
                desc(ChainAnchor.anchored_at),
                desc(ChainAnchor.created_at),
                desc(ChainAnchor.id),
            ).limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None
