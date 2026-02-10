"""Email accounts API: list and get (tenant-scoped).

Uses only injected get_email_account_repo; no manual construction.
Integration metadata for Gmail, Outlook, IMAP.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_email_account_repo
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.email_account_repo import (
    EmailAccountRepository,
)

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail=f"Missing required header: {name}")
    return x_tenant_id


@router.get("")
async def list_email_accounts(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    skip: int = 0,
    limit: int = 100,
    email_account_repo: EmailAccountRepository = Depends(get_email_account_repo),
):
    """List email accounts for tenant (paginated)."""
    accounts = await email_account_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return [
        {
            "id": a.id,
            "tenant_id": a.tenant_id,
            "subject_id": a.subject_id,
            "provider_type": a.provider_type,
            "email_address": a.email_address,
            "is_active": a.is_active,
            "sync_status": a.sync_status,
            "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
        }
        for a in accounts
    ]


@router.get("/{account_id}")
async def get_email_account(
    account_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    email_account_repo: EmailAccountRepository = Depends(get_email_account_repo),
):
    """Get email account by id (tenant-scoped)."""
    account = await email_account_repo.get_by_id_and_tenant(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    return {
        "id": account.id,
        "tenant_id": account.tenant_id,
        "subject_id": account.subject_id,
        "provider_type": account.provider_type,
        "email_address": account.email_address,
        "is_active": account.is_active,
        "sync_status": account.sync_status,
        "last_sync_at": (
            account.last_sync_at.isoformat() if account.last_sync_at else None
        ),
        "oauth_status": getattr(account, "oauth_status", None),
    }
