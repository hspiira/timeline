"""Repository for TenantIntegrityProfileHistory."""

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models import TenantIntegrityProfileHistory
from app.infrastructure.persistence.repositories.base import BaseRepository


class TenantIntegrityProfileHistoryRepository(
    BaseRepository[TenantIntegrityProfileHistory]
):
    """Append-only history of tenant integrity profile changes."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, TenantIntegrityProfileHistory)

    async def create_entry(
        self,
        *,
        tenant_id: str,
        previous_profile: str | None,
        new_profile: str,
        changed_by_user_id: str,
        change_reason: str | None,
        effective_from_seq: int,
        cooling_off_ends_at: datetime | None = None,
    ) -> TenantIntegrityProfileHistory:
        """Insert a new history row and return it."""
        now = datetime.now(timezone.utc)
        obj = TenantIntegrityProfileHistory(
            tenant_id=tenant_id,
            previous_profile=previous_profile,
            new_profile=new_profile,
            changed_at=now,
            changed_by_user_id=changed_by_user_id,
            change_reason=change_reason,
            effective_from_seq=effective_from_seq,
            cooling_off_ends_at=cooling_off_ends_at,
        )
        created = await self.create(obj)
        return created

    async def get_latest_for_tenant(
        self,
        tenant_id: str,
    ) -> TenantIntegrityProfileHistory | None:
        """Return the most recent history row for the tenant, or None."""
        result = await self.db.execute(
            select(TenantIntegrityProfileHistory)
            .where(TenantIntegrityProfileHistory.tenant_id == tenant_id)
            .order_by(desc(TenantIntegrityProfileHistory.changed_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(
        self,
        tenant_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TenantIntegrityProfileHistory]:
        """Return history rows for tenant ordered by changed_at desc."""
        result = await self.db.execute(
            select(TenantIntegrityProfileHistory)
            .where(TenantIntegrityProfileHistory.tenant_id == tenant_id)
            .order_by(desc(TenantIntegrityProfileHistory.changed_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

