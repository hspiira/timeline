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

    async def create_email_account(
        self,
        tenant_id: str,
        subject_id: str,
        provider_type: str,
        email_address: str,
        credentials_encrypted: str,
        connection_params: dict | None = None,
        oauth_provider_config_id: str | None = None,
    ) -> EmailAccount:
        """Create an email account (caller does not need to import EmailAccount ORM)."""
        account = EmailAccount(
            tenant_id=tenant_id,
            subject_id=subject_id,
            provider_type=provider_type.strip().lower(),
            email_address=email_address.strip(),
            credentials_encrypted=credentials_encrypted,
            connection_params=connection_params,
            oauth_provider_config_id=oauth_provider_config_id,
            is_active=True,
            sync_status="idle",
        )
        return await self.create(account)

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
