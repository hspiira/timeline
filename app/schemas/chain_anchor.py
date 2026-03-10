"""Pydantic schemas for chain anchor API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChainAnchorListItem(BaseModel):
    """Single anchor in list (no receipt blob)."""

    id: str
    tenant_id: str
    subject_id: str | None = None  # None = tenant-level anchor
    chain_tip_hash: str
    anchored_at: datetime
    tsa_url: str
    tsa_serial: str | None
    status: str
    error_message: str | None
    created_at: datetime


class ChainAnchorLatestResponse(BaseModel):
    """Latest confirmed anchor with base64-encoded receipt for offline verification."""

    id: str
    tenant_id: str
    subject_id: str | None = None  # None = tenant-level anchor
    chain_tip_hash: str
    anchored_at: datetime
    tsa_url: str
    tsa_serial: str | None
    status: str
    tsa_receipt_base64: str | None = Field(
        default=None,
        description="Raw DER TimeStampToken, base64-encoded; null if not confirmed.",
    )
    created_at: datetime
