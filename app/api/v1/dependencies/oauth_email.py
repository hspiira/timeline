"""OAuth provider config, state, and email account dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import (
    EnvelopeEncryptor,
    OAuthStateManager,
)
from app.infrastructure.external.email.oauth_drivers import OAuthDriverRegistry
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    EmailAccountRepository,
    OAuthProviderConfigRepository,
    OAuthStateRepository,
)
from app.infrastructure.services import SystemAuditService
from app.infrastructure.services.email_account_service import EmailAccountService
from app.infrastructure.services.oauth_config_service import OAuthConfigService

from . import auth
from . import db as db_deps


async def get_oauth_provider_config_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for read operations."""
    return OAuthProviderConfigRepository(db, audit_service=None)


async def get_oauth_provider_config_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for create/update/delete (transactional)."""
    return OAuthProviderConfigRepository(db, audit_service=audit_svc)


async def get_oauth_state_repo(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    state_manager: OAuthStateManager = Depends(auth.get_oauth_state_manager),
) -> OAuthStateRepository:
    """OAuth state repository for authorize/callback (transactional)."""
    return OAuthStateRepository(db, state_manager=state_manager)


async def get_email_account_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailAccountRepository:
    """Email account repository for read operations (list, get by id)."""
    return EmailAccountRepository(db)


async def get_email_account_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EmailAccountRepository:
    """Email account repository for create/update/delete (transactional)."""
    return EmailAccountRepository(db)


async def get_oauth_config_service(
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    state_repo: Annotated[
        OAuthStateRepository, Depends(get_oauth_state_repo)
    ],
    envelope_encryptor: Annotated[EnvelopeEncryptor, Depends(auth.get_envelope_encryptor)],
    driver_registry: Annotated[
        OAuthDriverRegistry, Depends(auth.get_oauth_driver_registry)
    ],
) -> OAuthConfigService:
    """OAuth config and flow service (composition root)."""
    return OAuthConfigService(
        oauth_repo=oauth_repo,
        state_repo=state_repo,
        envelope_encryptor=envelope_encryptor,
        driver_registry=driver_registry,
    )


def get_email_account_service(
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    credential_encryptor: CredentialEncryptor = Depends(auth.get_credential_encryptor),
) -> EmailAccountService:
    """Email account service (composition root)."""
    return EmailAccountService(
        email_account_repo=email_account_repo,
        credential_encryptor=credential_encryptor,
    )
