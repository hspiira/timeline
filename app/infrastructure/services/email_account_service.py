"""Email account service: create with encryption, mark sync pending.

Keeps credential encryption and ORM updates out of the API layer.
"""

from __future__ import annotations

from typing import Any

from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.repositories.email_account_repo import (
    EmailAccountRepository,
)


class EmailAccountService:
    """Create email accounts (encrypt credentials) and mark sync pending."""

    def __init__(
        self,
        email_account_repo: EmailAccountRepository,
        credential_encryptor: Any,
    ) -> None:
        self._repo = email_account_repo
        self._encryptor = credential_encryptor

    async def create_email_account(
        self,
        tenant_id: str,
        subject_id: str,
        provider_type: str,
        email_address: str,
        credentials_plain: dict[str, Any],
        connection_params: dict | None = None,
        oauth_provider_config_id: str | None = None,
    ) -> Any:
        """Encrypt credentials and create email account. Returns created account."""
        credentials_encrypted = self._encryptor.encrypt(credentials_plain)
        return await self._repo.create_email_account(
            tenant_id=tenant_id,
            subject_id=subject_id,
            provider_type=provider_type,
            email_address=email_address,
            credentials_encrypted=credentials_encrypted,
            connection_params=connection_params,
            oauth_provider_config_id=oauth_provider_config_id,
        )

    async def mark_sync_pending(self, account_id: str, tenant_id: str) -> None:
        """Set account sync_status to pending and clear error. Raises ResourceNotFoundException if not found."""
        from app.shared.utils.datetime import utc_now

        account = await self._repo.get_by_id_and_tenant(account_id, tenant_id)
        if not account:
            raise ResourceNotFoundException("email_account", account_id)
        account.sync_status = "pending"
        account.sync_started_at = utc_now()
        account.sync_error = None
        await self._repo.update(account)

    async def run_sync_now(self, account_id: str, tenant_id: str) -> None:
        """Run sync for the account (mark pending and execute sync). Use for in-process or background task.

        Currently marks the account pending. Full sync (fetch messages, create events,
        update completion state) is planned for Phase 7; see docs/PROJECT_OVERVIEW.md.
        """
        await self.mark_sync_pending(account_id, tenant_id)
        # Phase 7: run actual sync (fetch messages, create events, update completion state)
