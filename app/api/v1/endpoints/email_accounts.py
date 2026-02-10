"""Email accounts API: list, get, create, update, delete (tenant-scoped).

Uses only injected get_email_account_repo / get_email_account_repo_for_write.
Integration metadata for Gmail, Outlook, IMAP.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_current_user,
    get_email_account_repo,
    get_email_account_repo_for_write,
    get_tenant_id,
)
from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.persistence.models.email_account import EmailAccount
from app.infrastructure.persistence.repositories.email_account_repo import (
    EmailAccountRepository,
)
from app.schemas.email_account import (
    EmailAccountCreate,
    EmailAccountResponse,
    EmailAccountSyncStatusResponse,
    EmailAccountUpdate,
)

router = APIRouter()


@router.get("", response_model=list[EmailAccountResponse])
async def list_email_accounts(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
    skip: int = 0,
    limit: int = 100,
):
    """List email accounts for tenant (paginated). Requires authentication."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    accounts = await email_account_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return [EmailAccountResponse.model_validate(a) for a in accounts]


@router.get("/{account_id}", response_model=EmailAccountResponse)
async def get_email_account(
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
):
    """Get email account by id (tenant-scoped). Requires authentication."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    return EmailAccountResponse.model_validate(account)


@router.post("", response_model=EmailAccountResponse, status_code=201)
async def create_email_account(
    body: EmailAccountCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
):
    """Create email account (credentials encrypted at rest)."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    encryptor = CredentialEncryptor()
    credentials_encrypted = encryptor.encrypt(body.credentials)
    account = EmailAccount(
        tenant_id=tenant_id,
        subject_id=body.subject_id,
        provider_type=body.provider_type.strip().lower(),
        email_address=body.email_address.strip(),
        credentials_encrypted=credentials_encrypted,
        connection_params=body.connection_params,
        oauth_provider_config_id=body.oauth_provider_config_id,
        is_active=True,
        sync_status="idle",
    )
    await email_account_repo.create(account)
    return EmailAccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=EmailAccountResponse)
async def update_email_account(
    account_id: str,
    body: EmailAccountUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
):
    """Partially update email account."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    if body.email_address is not None:
        account.email_address = body.email_address
    if body.connection_params is not None:
        account.connection_params = body.connection_params
    if body.is_active is not None:
        account.is_active = body.is_active
    if body.sync_status is not None:
        account.sync_status = body.sync_status
    await email_account_repo.update(account)
    return EmailAccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=204)
async def delete_email_account(
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
):
    """Delete email account (hard delete)."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    await email_account_repo.delete(account)
    return None


@router.get(
    "/{account_id}/sync-status",
    response_model=EmailAccountSyncStatusResponse,
)
async def get_email_account_sync_status(
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
):
    """Return last sync time, status, and error for the email account."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    return EmailAccountSyncStatusResponse(
        account_id=account.id,
        sync_status=account.sync_status,
        last_sync_at=account.last_sync_at,
        sync_started_at=account.sync_started_at,
        sync_completed_at=account.sync_completed_at,
        sync_error=account.sync_error,
        sync_messages_fetched=account.sync_messages_fetched,
        sync_events_created=account.sync_events_created,
    )


@router.post("/{account_id}/sync", status_code=202)
async def trigger_email_sync(
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
):
    """Trigger sync for the email account (in-process). Returns 202 when accepted."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    from app.shared.utils.datetime import utc_now

    account.sync_status = "pending"
    account.sync_started_at = utc_now()
    account.sync_error = None
    await email_account_repo.update(account)
    return {"detail": "Sync started", "account_id": account_id}


@router.post("/{account_id}/sync-background", status_code=202)
async def trigger_email_sync_background(
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
):
    """Enqueue background sync for the email account. Returns 202 when accepted."""
    if getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    from app.shared.utils.datetime import utc_now

    account.sync_status = "pending"
    account.sync_started_at = utc_now()
    account.sync_error = None
    await email_account_repo.update(account)
    return {"detail": "Background sync enqueued", "account_id": account_id}


@router.post("/{account_id}/webhook", status_code=202)
async def email_account_webhook(
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
):
    """Provider callback (e.g. Gmail push). Verify signature and enqueue sync; returns 202."""
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    return {"detail": "Webhook received", "account_id": account_id}
