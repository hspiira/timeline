"""Chain anchor repository. RFC 3161 TSA receipt storage per tenant chain tip."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import desc

from app.application.dtos.chain_anchor import ChainAnchorResult
from app.infrastructure.persistence.models.chain_anchor import ChainAnchor
from app.infrastructure.persistence.repositories.base import BaseRepository


def _to_result(a: ChainAnchor) -> ChainAnchorResult:
    """Map ORM to DTO."""
    return ChainAnchorResult(
        id=a.id,
        tenant_id=a.tenant_id,
        subject_id=a.subject_id,
        chain_tip_hash=a.chain_tip_hash,
        anchored_at=a.anchored_at,
        tsa_url=a.tsa_url,
        tsa_receipt=a.tsa_receipt,
        tsa_serial=a.tsa_serial,
        status=a.status,
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
        anchored_at: datetime,
        tsa_url: str,
        *,
        subject_id: str | None = None,
    ) -> ChainAnchorResult:
        """Create a pending anchor row. subject_id=None for tenant-level. Raises IntegrityError if unique (tenant_id, tip) or (tenant_id, subject_id, tip) already exists."""
        anchor = ChainAnchor(
            tenant_id=tenant_id,
            subject_id=subject_id,
            chain_tip_hash=chain_tip_hash,
            anchored_at=anchored_at,
            tsa_url=tsa_url,
            status="pending",
        )
        created = await self.create(anchor)
        return _to_result(created)

    async def update_confirmed(
        self, anchor_id: str, tsa_receipt: bytes, tsa_serial: str | None
    ) -> ChainAnchorResult | None:
        """Mark anchor as confirmed and store receipt; return updated result or None."""
        result = await self.db.execute(select(ChainAnchor).where(ChainAnchor.id == anchor_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = "confirmed"
        row.tsa_receipt = tsa_receipt
        row.tsa_serial = tsa_serial
        row.error_message = None
        await self.db.flush()
        await self.db.refresh(row)
        return _to_result(row)

    async def update_failed(self, anchor_id: str, error_message: str) -> ChainAnchorResult | None:
        """Mark anchor as failed; return updated result or None."""
        result = await self.db.execute(select(ChainAnchor).where(ChainAnchor.id == anchor_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = "failed"
        row.error_message = error_message
        await self.db.flush()
        await self.db.refresh(row)
        return _to_result(row)

    async def update_to_pending(self, anchor_id: str) -> ChainAnchorResult | None:
        """Set status to pending and clear error_message (for retry after failed)."""
        result = await self.db.execute(select(ChainAnchor).where(ChainAnchor.id == anchor_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = "pending"
        row.error_message = None
        await self.db.flush()
        await self.db.refresh(row)
        return _to_result(row)

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
        q = q.order_by(desc(ChainAnchor.anchored_at), desc(ChainAnchor.created_at)).offset(skip).limit(limit)
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
            ChainAnchor.status == "confirmed",
        )
        if tenant_level_only:
            q = q.where(ChainAnchor.subject_id.is_(None))
        result = await self.db.execute(
            q.order_by(desc(ChainAnchor.anchored_at), desc(ChainAnchor.created_at)).limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None
