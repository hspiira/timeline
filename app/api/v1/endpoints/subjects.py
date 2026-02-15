"""Subject API: thin routes delegating to SubjectService."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_create_subject_snapshot_use_case,
    get_get_subject_state_use_case,
    get_subject_erasure_service,
    get_subject_export_service,
    get_subject_service,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.state import (
    CreateSubjectSnapshotUseCase,
    GetSubjectStateUseCase,
)
from app.application.use_cases.subjects import (
    ErasureStrategy,
    SubjectErasureService,
    SubjectExportService,
    SubjectService,
)
from app.core.limiter import limit_writes
from app.domain.exceptions import ResourceNotFoundException, ValidationException
from app.schemas.subject import (
    SubjectCreateRequest,
    SubjectErasureRequest,
    SubjectResponse,
    SubjectSnapshotResponse,
    SubjectStateResponse,
    SubjectUpdate,
)

router = APIRouter()


@router.post("", response_model=SubjectResponse, status_code=201)
@limit_writes
async def create_subject(
    request: Request,
    body: SubjectCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: Annotated[SubjectService, Depends(get_subject_service)],
    _: Annotated[object, Depends(require_permission("subject", "create"))] = None,
):
    """Create a subject (tenant-scoped)."""
    created = await subject_svc.create_subject(
        tenant_id=tenant_id,
        subject_type=body.subject_type,
        external_ref=body.external_ref,
        display_name=body.display_name,
        attributes=body.attributes,
    )
    return SubjectResponse.model_validate(created)


@router.post("/{subject_id}/export")
@limit_writes
async def export_subject_data(
    request: Request,
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    export_svc: Annotated[
        SubjectExportService, Depends(get_subject_export_service)
    ],
    _: Annotated[object, Depends(require_permission("subject", "export"))] = None,
):
    """Export all data for the subject (GDPR): subject, events, document refs (no binary)."""
    try:
        result = await export_svc.export_subject_data(
            tenant_id=tenant_id,
            subject_id=subject_id,
        )
        return {
            "subject": result.subject,
            "events": result.events,
            "documents": result.documents,
            "exported_at": result.exported_at.isoformat(),
        }
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.post("/{subject_id}/erasure", status_code=204)
@limit_writes
async def erase_subject_data(
    request: Request,
    subject_id: str,
    body: SubjectErasureRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    erasure_svc: Annotated[
        SubjectErasureService, Depends(get_subject_erasure_service)
    ],
    _: Annotated[object, Depends(require_permission("subject", "erasure"))] = None,
):
    """Erase or anonymize subject data (GDPR). Body: {"strategy": "anonymize"|"delete"}."""
    try:
        strategy = ErasureStrategy(body.strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="strategy must be 'anonymize' or 'delete'",
        ) from None
    try:
        await erasure_svc.erase_subject_data(
            tenant_id=tenant_id,
            subject_id=subject_id,
            strategy=strategy,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.post(
    "/{subject_id}/snapshot",
    response_model=SubjectSnapshotResponse,
    status_code=201,
)
@limit_writes
async def create_subject_snapshot(
    request: Request,
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    snapshot_use_case: Annotated[
        CreateSubjectSnapshotUseCase, Depends(get_create_subject_snapshot_use_case)
    ],
    _: Annotated[object, Depends(require_permission("subject", "update"))] = None,
):
    """Create or replace the subject snapshot (on-demand state checkpoint). Fails if subject has no events."""
    try:
        result = await snapshot_use_case.create_snapshot(
            tenant_id=tenant_id,
            subject_id=subject_id,
        )
        return SubjectSnapshotResponse(
            id=result.id,
            subject_id=result.subject_id,
            snapshot_at_event_id=result.snapshot_at_event_id,
            event_count_at_snapshot=result.event_count_at_snapshot,
            created_at=result.created_at,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message) from None


@router.get("/{subject_id}/state", response_model=SubjectStateResponse)
async def get_subject_state(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    state_use_case: Annotated[
        GetSubjectStateUseCase, Depends(get_get_subject_state_use_case)
    ],
    _: Annotated[object, Depends(require_permission("subject", "read"))] = None,
    as_of: str | None = Query(
        default=None,
        description="ISO8601 datetime for time-travel (state as of this time)",
    ),
):
    """Get derived state for subject (event replay). Optional as_of for time-travel."""
    try:
        result = await state_use_case.get_current_state(
            tenant_id=tenant_id,
            subject_id=subject_id,
            as_of=as_of,
        )
        return SubjectStateResponse(
            state=result.state,
            last_event_id=result.last_event_id,
            event_count=result.event_count,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: Annotated[SubjectService, Depends(get_subject_service)],
    _: Annotated[object, Depends(require_permission("subject", "read"))] = None,
):
    """Get subject by id (tenant-scoped)."""
    try:
        subject = await subject_svc.get_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
        )
        return SubjectResponse.model_validate(subject)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.get("", response_model=list[SubjectResponse])
async def list_subjects(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: Annotated[SubjectService, Depends(get_subject_service)],
    _: Annotated[object, Depends(require_permission("subject", "read"))] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    subject_type: str | None = None,
):
    """List subjects for tenant (optional type filter)."""
    subjects = await subject_svc.list_subjects(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        subject_type=subject_type,
    )
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.put("/{subject_id}", response_model=SubjectResponse)
@limit_writes
async def update_subject(
    request: Request,
    subject_id: str,
    body: SubjectUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: Annotated[SubjectService, Depends(get_subject_service)],
    _: Annotated[object, Depends(require_permission("subject", "update"))] = None,
):
    """Update subject (e.g. external_ref, display_name, attributes). Tenant-scoped."""
    try:
        updated = await subject_svc.update_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
            external_ref=body.external_ref,
            display_name=body.display_name,
            attributes=body.attributes,
        )
        return SubjectResponse.model_validate(updated)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.delete("/{subject_id}", status_code=204)
@limit_writes
async def delete_subject(
    request: Request,
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: Annotated[SubjectService, Depends(get_subject_service)],
    _: Annotated[object, Depends(require_permission("subject", "delete"))] = None,
):
    """Delete subject. Tenant-scoped."""
    try:
        await subject_svc.delete_subject(tenant_id=tenant_id, subject_id=subject_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None
