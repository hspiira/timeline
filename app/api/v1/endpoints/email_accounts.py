"""Email accounts API: list, get, create, update, delete (tenant-scoped).

Uses only injected get_email_account_repo / get_email_account_repo_for_write.
Integration metadata for Gmail, Outlook, IMAP.
"""

import hmac
import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    CredentialEncryptor,
    get_credential_encryptor,
    get_email_account_repo,
    get_email_account_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.core.config import get_settings
from app.core.limiter import limit_writes
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
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
    skip: int = 0,
    limit: int = 100,
    _: Annotated[object, Depends(require_permission("email_account", "read"))] = None,
):
    """List email accounts for tenant (paginated)."""
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
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
    _: Annotated[object, Depends(require_permission("email_account", "read"))] = None,
):
    """Get email account by id (tenant-scoped)."""
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    return EmailAccountResponse.model_validate(account)


@router.post("", response_model=EmailAccountResponse, status_code=201)
@limit_writes
async def create_email_account(
    request: Request,
    body: EmailAccountCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    credential_encryptor: CredentialEncryptor = Depends(get_credential_encryptor),
    _: Annotated[object, Depends(require_permission("email_account", "create"))] = None,
):
    """Create email account (credentials encrypted at rest)."""
    credentials_encrypted = credential_encryptor.encrypt(body.credentials)
    account = await email_account_repo.create_email_account(
        tenant_id=tenant_id,
        subject_id=body.subject_id,
        provider_type=body.provider_type,
        email_address=body.email_address,
        credentials_encrypted=credentials_encrypted,
        connection_params=body.connection_params,
        oauth_provider_config_id=body.oauth_provider_config_id,
    )
    return EmailAccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=EmailAccountResponse)
@limit_writes
async def update_email_account(
    request: Request,
    account_id: str,
    body: EmailAccountUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("email_account", "update"))] = None,
):
    """Partially update email account."""
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
@limit_writes
async def delete_email_account(
    request: Request,
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("email_account", "delete"))] = None,
):
    """Delete email account (hard delete)."""
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
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
    _: Annotated[object, Depends(require_permission("email_account", "read"))] = None,
):
    """Return last sync time, status, and error for the email account."""
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


async def _mark_account_sync_pending(
    email_account_repo: EmailAccountRepository,
    account_id: str,
    tenant_id: str,
) -> None:
    """Set account to sync pending and persist. Raises HTTPException 404 if not found."""
    from app.shared.utils.datetime import utc_now

    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    account.sync_status = "pending"
    account.sync_started_at = utc_now()
    account.sync_error = None
    await email_account_repo.update(account)


@router.post("/{account_id}/sync", status_code=202)
@limit_writes
async def trigger_email_sync(
    request: Request,
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("email_account", "update"))] = None,
):
    """Trigger sync for the email account (in-process). Returns 202 when accepted."""
    await _mark_account_sync_pending(email_account_repo, account_id, tenant_id)
    return {"detail": "Sync started", "account_id": account_id}


@router.post("/{account_id}/sync-background", status_code=202)
@limit_writes
async def trigger_email_sync_background(
    request: Request,
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    _: Annotated[object, Depends(require_permission("email_account", "update"))] = None,
):
    """Enqueue background sync for the email account. Returns 202 when accepted."""
    await _mark_account_sync_pending(email_account_repo, account_id, tenant_id)
    return {"detail": "Background sync enqueued", "account_id": account_id}


def _verify_webhook_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """Return True if X-Webhook-Signature-256 matches HMAC-SHA256(secret, body)."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header[7:].strip(), expected)


@router.post("/{account_id}/webhook", status_code=202)
@limit_writes
async def email_account_webhook(
    request: Request,
    account_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo)
    ],
):
    """Provider callback (e.g. Gmail push). If EMAIL_WEBHOOK_SECRET is set, X-Webhook-Signature-256 is required."""
    body = await request.body()
    settings = get_settings()
    if settings.email_webhook_secret:
        sig = request.headers.get("X-Webhook-Signature-256")
        secret = settings.email_webhook_secret.get_secret_value()
        if not _verify_webhook_signature(body, sig, secret):
            raise HTTPException(status_code=401, detail="Invalid or missing webhook signature")
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    return {"detail": "Webhook received", "account_id": account_id}
