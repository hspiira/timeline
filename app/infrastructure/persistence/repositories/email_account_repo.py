"""Email account repository. Read and list by tenant/subject."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.email_account import EmailAccount
from app.infrastructure.persistence.repositories.base import BaseRepository


class EmailAccountRepository(BaseRepository[EmailAccount]):
    """Email account repository (integration metadata for Gmail, Outlook, IMAP)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, EmailAccount)

    async def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EmailAccount]:
        """Return email accounts for tenant (paginated)."""
        result = await self.db.execute(
            select(EmailAccount)
            .where(EmailAccount.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(EmailAccount.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_and_tenant(
        self, account_id: str, tenant_id: str
    ) -> EmailAccount | None:
        """Return email account by id if it belongs to tenant."""
        result = await self.db.execute(
            select(EmailAccount).where(
                EmailAccount.id == account_id,
                EmailAccount.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
