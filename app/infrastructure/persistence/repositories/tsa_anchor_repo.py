"""TSA anchor repository. Stores RFC 3161 TimeStampTokens for integrity epochs/batches."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models import TsaAnchor
from app.infrastructure.persistence.repositories.base import BaseRepository


class TsaAnchorRepository(BaseRepository[TsaAnchor]):
    """Repository for tsa_anchor table (chain integrity TSA receipts)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, TsaAnchor)

    async def create_anchor(
        self,
        tenant_id: str,
        anchor_type: str,
        payload_hash: str,
        tsa_token: bytes,
        tsa_provider: str,
        tsa_reported_time: datetime,
        *,
        tsa_serial: str | None = None,
        anchored_at: datetime | None = None,
    ) -> TsaAnchor:
        """Insert a TSA anchor row; returns the created ORM entity."""
        anchor = TsaAnchor(
            tenant_id=tenant_id,
            anchor_type=anchor_type,
            payload_hash=payload_hash,
            tsa_token=tsa_token,
            tsa_provider=tsa_provider,
            tsa_serial=tsa_serial,
            anchored_at=anchored_at or datetime.now(timezone.utc),
            tsa_reported_time=tsa_reported_time,
            verification_status="PENDING",
        )
        return await self.create(anchor)

    async def update_verification_status(
        self,
        anchor_id: str,
        status: str,
        *,
        verified_at: datetime | None = None,
    ) -> TsaAnchor | None:
        """Update verification_status (and optionally verified_at). Returns updated row or None."""
        row = await self.get_by_id(anchor_id)
        if not row:
            return None
        row.verification_status = status
        if verified_at is not None:
            row.verified_at = verified_at
        await self.db.flush()
        await self.db.refresh(row)
        return row
