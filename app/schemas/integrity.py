"""Schemas for integrity read/verify/proof endpoints."""

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import IntegrityProfile


class IntegrityEpochItem(BaseModel):
    """Integrity epoch summary for a subject."""

    id: str
    epoch_number: int
    status: str
    event_count: int
    opened_at: datetime
    sealed_at: datetime | None = None
    tsa_anchor_id: str | None = None
    merkle_root: str | None = None
    profile_snapshot: IntegrityProfile


class IntegrityVerificationSummary(BaseModel):
    """Summary of chain verification for a subject."""

    subject_id: str
    tenant_id: str
    total_events: int
    valid_events: int
    invalid_events: int
    is_chain_valid: bool
    verified_at: datetime


class MerkleProofStep(BaseModel):
    """One step in Merkle proof path."""

    sibling_hash: str
    is_left_sibling: bool


class MerkleProofResponse(BaseModel):
    """Merkle proof for a LEGAL_GRADE event."""

    tenant_id: str
    subject_id: str
    epoch_id: str
    event_seq: int
    leaf_hash: str
    root_hash: str
    tsa_anchor_id: str | None = None
    steps: list[MerkleProofStep]


class ChainRepairCreateRequest(BaseModel):
    """Request body for initiating a chain repair."""

    epoch_id: str
    break_at_event_seq: int
    break_reason: str
    repair_reference: str | None = None


class ChainRepairResponse(BaseModel):
    """Chain repair record returned from C7/C8 endpoints."""

    id: str
    tenant_id: str
    epoch_id: str
    break_at_event_seq: int
    break_reason: str
    repair_status: str
    repair_initiated_by: str
    repair_approved_by: str | None
    approval_required: bool
    repair_reference: str | None
    repair_completed_at: datetime | None
    new_epoch_id: str | None

