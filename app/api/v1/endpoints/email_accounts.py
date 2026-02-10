"""Email accounts API: list and get (tenant-scoped).

Uses only injected get_email_account_repo; no manual construction.
Integration metadata for Gmail, Outlook, IMAP.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_current_user,
    get_email_account_repo,
    get_tenant_id,
)
from app.infrastructure.persistence.repositories.email_account_repo import (
    EmailAccountRepository,
)
from app.schemas.email_account import EmailAccountResponse

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
