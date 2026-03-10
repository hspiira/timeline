"""Chain anchor API: list and latest (RFC 3161 TSA receipts)."""

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.dependencies import (
    get_chain_anchor_repo,
    get_verified_tenant_id,
    require_permission,
)
from app.application.dtos.chain_anchor import ChainAnchorResult
from app.infrastructure.persistence.repositories import ChainAnchorRepository
from app.schemas.chain_anchor import ChainAnchorLatestResponse, ChainAnchorListItem

router = APIRouter()


def _to_list_item(a: ChainAnchorResult) -> ChainAnchorListItem:
    return ChainAnchorListItem(
        id=a.id,
        tenant_id=a.tenant_id,
        subject_id=a.subject_id,
        chain_tip_hash=a.chain_tip_hash,
        anchored_at=a.anchored_at,
        tsa_url=a.tsa_url,
        tsa_serial=a.tsa_serial,
        status=a.status,
        error_message=a.error_message,
        created_at=a.created_at,
    )


@router.get(
    "/{tenant_id}/chain-anchors",
    response_model=list[ChainAnchorListItem],
    summary="List chain anchors for tenant",
)
async def list_chain_anchors(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    anchor_repo: Annotated[ChainAnchorRepository, Depends(get_chain_anchor_repo)],
    _: Annotated[None, Depends(require_permission("chain_anchor", "read"))],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[ChainAnchorListItem]:
    """List all anchors for the tenant (newest first), paginated."""
    anchors = await anchor_repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return [_to_list_item(a) for a in anchors]


@router.get(
    "/{tenant_id}/chain-anchors/latest",
    response_model=ChainAnchorLatestResponse,
    summary="Get latest confirmed chain anchor",
)
async def get_latest_chain_anchor(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    anchor_repo: Annotated[ChainAnchorRepository, Depends(get_chain_anchor_repo)],
    _: Annotated[None, Depends(require_permission("chain_anchor", "read"))],
) -> ChainAnchorLatestResponse:
    """Return the most recent confirmed anchor with base64-encoded receipt for offline verification."""
    anchor = await anchor_repo.get_latest_confirmed(tenant_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="No confirmed chain anchor found for this tenant")
    receipt_b64 = base64.standard_b64encode(anchor.tsa_receipt).decode() if anchor.tsa_receipt else None
    return ChainAnchorLatestResponse(
        id=anchor.id,
        tenant_id=anchor.tenant_id,
        subject_id=anchor.subject_id,
        chain_tip_hash=anchor.chain_tip_hash,
        anchored_at=anchor.anchored_at,
        tsa_url=anchor.tsa_url,
        tsa_serial=anchor.tsa_serial,
        status=anchor.status,
        tsa_receipt_base64=receipt_b64,
        created_at=anchor.created_at,
    )
