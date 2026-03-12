"""Integrity API: epochs, verification, and Merkle proofs."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_chain_repair_service,
    get_event_repo,
    get_integrity_epoch_repo,
    get_tenant_id,
    get_verification_service,
    get_tenant_integrity_history_repo,
    get_current_user,
    require_permission,
)
from app.application.services.merkle_service import MerkleService
from app.core.config import get_settings
from app.domain.enums import IntegrityEpochStatus, IntegrityProfile
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories import (
    ChainRepairLogRepository,
    EventRepository,
    IntegrityEpochRepository,
    MerkleNodeRepository,
    TsaAnchorRepository,
)
from app.infrastructure.services.tsa_service import TsaService
from app.schemas.integrity import (
    ChainRepairCreateRequest,
    ChainRepairResponse,
    IntegrityEpochItem,
    IntegrityVerificationDetail,
    IntegrityVerificationSummary,
    MerkleProofResponse,
    MerkleProofStep,
    VerificationEventResult,
)

router = APIRouter()


@router.get(
    "/integrity/epochs/{subject_id}",
    response_model=list[IntegrityEpochItem],
)
async def list_integrity_epochs_for_subject(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    epoch_repo: Annotated[IntegrityEpochRepository, Depends(get_integrity_epoch_repo)],
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List integrity epochs for a subject under the current tenant (paginated)."""
    rows = await epoch_repo.list_for_subject(
        tenant_id=tenant_id,
        subject_id=subject_id,
        skip=skip,
        limit=limit,
    )
    items: list[IntegrityEpochItem] = []
    for row in rows:
        profile = IntegrityProfile(row.profile_snapshot)
        items.append(
            IntegrityEpochItem(
                id=row.id,
                epoch_number=row.epoch_number,
                status=row.status,
                event_count=row.event_count,
                opened_at=row.opened_at,
                sealed_at=row.sealed_at,
                tsa_anchor_id=row.tsa_anchor_id,
                merkle_root=row.merkle_root,
                profile_snapshot=profile,
            )
        )
    return items


@router.get(
    "/integrity/verify/{subject_id}",
    response_model=IntegrityVerificationSummary,
)
async def verify_subject_integrity(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    verification_service=Depends(get_verification_service),
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Verify hash chain integrity for a subject (events only, no TSA/Merkle)."""
    result = await verification_service.verify_subject_chain(
        subject_id=subject_id,
        tenant_id=tenant_id,
    )
    return IntegrityVerificationSummary(
        subject_id=subject_id,
        tenant_id=tenant_id,
        total_events=result.total_events,
        valid_events=result.valid_events,
        invalid_events=result.invalid_events,
        is_chain_valid=result.is_chain_valid,
        verified_at=result.verified_at,
    )


@router.get(
    "/integrity/verify/{subject_id}/detail",
    response_model=IntegrityVerificationDetail,
)
async def verify_subject_integrity_detail(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    verification_service=Depends(get_verification_service),
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Verify hash chain integrity for a subject and return per-event results."""
    result = await verification_service.verify_subject_chain(
        subject_id=subject_id,
        tenant_id=tenant_id,
    )
    return IntegrityVerificationDetail(
        subject_id=subject_id,
        tenant_id=tenant_id,
        total_events=result.total_events,
        valid_events=result.valid_events,
        invalid_events=result.invalid_events,
        is_chain_valid=result.is_chain_valid,
        verified_at=result.verified_at,
        events=[
            VerificationEventResult(
                event_id=r.event_id,
                event_type=r.event_type,
                event_time=r.event_time,
                sequence=r.sequence,
                is_valid=r.is_valid,
                error_type=r.error_type,
                error_message=r.error_message,
                expected_hash=r.expected_hash,
                actual_hash=r.actual_hash,
                previous_hash=r.previous_hash,
            )
            for r in result.event_results
        ],
    )


@router.get(
    "/integrity/proof/{event_seq}",
    response_model=MerkleProofResponse,
)
async def get_merkle_proof_for_event(
    event_seq: int,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db=Depends(get_db),
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Return Merkle proof for a LEGAL_GRADE event identified by event_seq within its epoch."""
    async for session in db:
        event_repo = EventRepository(session)
        epoch_repo = IntegrityEpochRepository(session)
        merkle_repo = MerkleNodeRepository(session)
        tsa_anchor_repo = TsaAnchorRepository(session)

        # Find event by tenant and event_seq.
        event = await event_repo.get_by_tenant_and_seq(tenant_id, event_seq)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        subject_id = event.subject_id
        epoch_id = event.epoch_id
        if epoch_id is None:
            raise HTTPException(
                status_code=400,
                detail="Event is not associated with an integrity epoch",
            )

        epoch = await epoch_repo.get_by_id(epoch_id)
        if not epoch:
            raise HTTPException(status_code=404, detail="Epoch not found")
        if IntegrityProfile(epoch.profile_snapshot) is not IntegrityProfile.LEGAL_GRADE:
            raise HTTPException(
                status_code=400,
                detail="Merkle proof is only available for LEGAL_GRADE epochs",
            )
        if epoch.status != IntegrityEpochStatus.SEALED:
            raise HTTPException(
                status_code=400,
                detail="Epoch not sealed; Merkle proof not available yet",
            )

        merkle_service = MerkleService(event_repo=event_repo, merkle_repo=merkle_repo)
        proof_steps = await merkle_service.generate_proof(epoch_id, event_seq)
        if not proof_steps and epoch.merkle_root:
            raise HTTPException(
                status_code=500,
                detail="Merkle tree incomplete for this epoch",
            )

        leaf_hash = event.merkle_leaf_hash or event.hash
        root_hash = epoch.merkle_root or ""
        steps = [
            MerkleProofStep(sibling_hash=s.sibling_hash, is_left_sibling=s.is_left_sibling)
            for s in proof_steps
        ]

        return MerkleProofResponse(
            tenant_id=tenant_id,
            subject_id=subject_id,
            epoch_id=epoch_id,
            event_seq=event_seq,
            leaf_hash=leaf_hash,
            root_hash=root_hash,
            tsa_anchor_id=epoch.tsa_anchor_id,
            steps=steps,
        )


@router.post(
    "/integrity/repair",
    response_model=ChainRepairResponse,
)
async def initiate_chain_repair(
    body: ChainRepairCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    epoch_repo: Annotated[IntegrityEpochRepository, Depends(get_integrity_epoch_repo)],
    current_user=Depends(get_current_user),
    chain_repair_svc=Depends(get_chain_repair_service),
    _: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
):
    """Initiate a chain repair request for a specific epoch."""
    epoch = await epoch_repo.get_by_id(body.epoch_id)
    if not epoch or epoch.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Epoch not found")
    profile = IntegrityProfile(epoch.profile_snapshot)

    record = await chain_repair_svc.initiate_repair(
        tenant_id=tenant_id,
        epoch_id=body.epoch_id,
        break_at_event_seq=body.break_at_event_seq,
        break_reason=body.break_reason,
        initiated_by=current_user.id,
        profile=profile,
        repair_reference=body.repair_reference,
    )
    return ChainRepairResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        epoch_id=record.epoch_id,
        break_at_event_seq=record.break_at_event_seq,
        break_reason=record.break_reason,
        repair_status=record.repair_status,
        repair_initiated_by=record.repair_initiated_by,
        repair_approved_by=record.repair_approved_by,
        approval_required=record.approval_required,
        repair_reference=record.repair_reference,
        repair_completed_at=record.repair_completed_at,
        new_epoch_id=record.new_epoch_id,
    )


@router.post(
    "/integrity/repair/{repair_id}/approve",
    response_model=ChainRepairResponse,
)
async def approve_chain_repair(
    repair_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user=Depends(get_current_user),
    chain_repair_svc=Depends(get_chain_repair_service),
    _: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
):
    """Approve a chain repair request (four-eyes rule)."""
    try:
        record = await chain_repair_svc.approve_repair(
            repair_id, approver_id=current_user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Repair not found")
    return ChainRepairResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        epoch_id=record.epoch_id,
        break_at_event_seq=record.break_at_event_seq,
        break_reason=record.break_reason,
        repair_status=record.repair_status,
        repair_initiated_by=record.repair_initiated_by,
        repair_approved_by=record.repair_approved_by,
        approval_required=record.approval_required,
        repair_reference=record.repair_reference,
        repair_completed_at=record.repair_completed_at,
        new_epoch_id=record.new_epoch_id,
    )


@router.get(
    "/integrity/repair/{repair_id}",
    response_model=ChainRepairResponse,
)
async def get_chain_repair(
    repair_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    chain_repair_svc=Depends(get_chain_repair_service),
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Return a chain repair record by id."""
    try:
        record = await chain_repair_svc.get_repair(repair_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Repair not found")
    return ChainRepairResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        epoch_id=record.epoch_id,
        break_at_event_seq=record.break_at_event_seq,
        break_reason=record.break_reason,
        repair_status=record.repair_status,
        repair_initiated_by=record.repair_initiated_by,
        repair_approved_by=record.repair_approved_by,
        approval_required=record.approval_required,
        repair_reference=record.repair_reference,
        repair_completed_at=record.repair_completed_at,
        new_epoch_id=record.new_epoch_id,
    )


@router.post(
    "/integrity/repair/{repair_id}/complete",
    response_model=ChainRepairResponse,
)
async def complete_chain_repair(
    repair_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    chain_repair_svc=Depends(get_chain_repair_service),
    _: Annotated[object, Depends(require_permission("tenant", "update"))] = None,
):
    """Complete a chain repair. Currently not implemented; returns 501."""
    try:
        await chain_repair_svc.complete_repair(repair_id)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    # Once implemented, this should mirror get_chain_repair to return the updated record.

