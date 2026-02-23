"""Subject API: thin routes delegating to SubjectService."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_create_subject_snapshot_use_case,
    get_get_subject_state_use_case,
    get_run_snapshot_job_use_case,
    get_subject_erasure_service,
    get_subject_export_service,
    get_subject_relationship_service,
    get_subject_service,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.state import (
    CreateSubjectSnapshotUseCase,
    GetSubjectStateUseCase,
    RunSnapshotJobUseCase,
)
from app.application.use_cases.state.run_snapshot_job import (
    SNAPSHOT_JOB_DEFAULT_LIMIT,
    SNAPSHOT_JOB_MAX_LIMIT,
)
from app.application.use_cases.subjects import (
    ErasureStrategy,
    SubjectErasureService,
    SubjectExportService,
    SubjectRelationshipService,
    SubjectService,
)
from app.core.limiter import limit_writes
from app.domain.exceptions import ResourceNotFoundException, ValidationException
from app.schemas.subject import (
    ExportSubjectResponse,
    SubjectCreateRequest,
    SubjectErasureRequest,
    SubjectResponse,
    SubjectSnapshotResponse,
    SnapshotRunResponse,
    SubjectStateResponse,
    SubjectUpdate,
)
from app.schemas.subject_relationship import (
    SubjectRelationshipCreateRequest,
    SubjectRelationshipListItem,
    SubjectRelationshipResponse,
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


@router.post("/snapshots/run", response_model=SnapshotRunResponse)
@limit_writes
async def run_snapshot_job(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    job_use_case: Annotated[
        RunSnapshotJobUseCase, Depends(get_run_snapshot_job_use_case)
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=SNAPSHOT_JOB_MAX_LIMIT,
            description="Max subjects to process",
        ),
    ] = SNAPSHOT_JOB_DEFAULT_LIMIT,
    _: Annotated[object, Depends(require_permission("subject", "update"))] = None,
):
    """Run batch snapshot creation for the current tenant. Call from cron or scripts."""
    result = await job_use_case.run(tenant_id=tenant_id, limit=limit)
    return SnapshotRunResponse(
        tenant_id=result.tenant_id,
        subjects_processed=result.subjects_processed,
        snapshots_created_or_updated=result.snapshots_created_or_updated,
        skipped_no_events=result.skipped_no_events,
        error_count=result.error_count,
        error_subject_ids=list(result.error_subject_ids),
    )


@router.post("/{subject_id}/export", response_model=ExportSubjectResponse)
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
        return ExportSubjectResponse(
            subject=result.subject,
            events=result.events,
            documents=result.documents,
            exported_at=result.exported_at.isoformat(),
        )
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
    workflow_instance_id: str | None = Query(
        default=None,
        description="Scope state to this workflow instance (stream).",
    ),
):
    """Get derived state for subject (event replay). Optional as_of and workflow_instance_id."""
    try:
        result = await state_use_case.get_current_state(
            tenant_id=tenant_id,
            subject_id=subject_id,
            as_of=as_of,
            workflow_instance_id=workflow_instance_id,
        )
        return SubjectStateResponse(
            state=result.state,
            last_event_id=result.last_event_id,
            event_count=result.event_count,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.get(
    "/{subject_id}/relationships",
    response_model=list[SubjectRelationshipListItem],
)
async def list_subject_relationships(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    relationship_svc: Annotated[
        SubjectRelationshipService, Depends(get_subject_relationship_service)
    ],
    _: Annotated[object, Depends(require_permission("subject", "read"))] = None,
    as_source: bool = Query(True, description="Include relationships where subject is source"),
    as_target: bool = Query(True, description="Include relationships where subject is target"),
    relationship_kind: str | None = Query(
        default=None,
        description="Filter by relationship kind",
    ),
):
    """List relationships for a subject (tenant-scoped)."""
    try:
        items = await relationship_svc.list_relationships(
            tenant_id=tenant_id,
            subject_id=subject_id,
            as_source=as_source,
            as_target=as_target,
            relationship_kind=relationship_kind,
        )
        return [
            SubjectRelationshipListItem(
                id=r.id,
                tenant_id=r.tenant_id,
                source_subject_id=r.source_subject_id,
                target_subject_id=r.target_subject_id,
                relationship_kind=r.relationship_kind,
                payload=r.payload,
                created_at=r.created_at,
            )
            for r in items
        ]
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None


@router.post(
    "/{subject_id}/relationships",
    response_model=SubjectRelationshipResponse,
    status_code=201,
)
@limit_writes
async def add_subject_relationship(
    request: Request,
    subject_id: str,
    body: SubjectRelationshipCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    relationship_svc: Annotated[
        SubjectRelationshipService, Depends(get_subject_relationship_service)
    ],
    _: Annotated[object, Depends(require_permission("subject", "update"))] = None,
):
    """Add a relationship from this subject to target (tenant-scoped)."""
    try:
        created = await relationship_svc.add_relationship(
            tenant_id=tenant_id,
            source_subject_id=subject_id,
            target_subject_id=body.target_subject_id,
            relationship_kind=body.relationship_kind,
            payload=body.payload,
        )
        return SubjectRelationshipResponse(
            id=created.id,
            tenant_id=created.tenant_id,
            source_subject_id=created.source_subject_id,
            target_subject_id=created.target_subject_id,
            relationship_kind=created.relationship_kind,
            payload=created.payload,
            created_at=created.created_at,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found") from None
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message) from None


@router.delete("/{subject_id}/relationships", status_code=204)
@limit_writes
async def remove_subject_relationship(
    request: Request,
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    relationship_svc: Annotated[
        SubjectRelationshipService, Depends(get_subject_relationship_service)
    ],
    _: Annotated[object, Depends(require_permission("subject", "update"))] = None,
    target_subject_id: str = Query(..., description="Target subject ID"),
    relationship_kind: str = Query(..., description="Relationship kind"),
):
    """Remove a relationship (tenant-scoped)."""
    deleted = await relationship_svc.remove_relationship(
        tenant_id=tenant_id,
        source_subject_id=subject_id,
        target_subject_id=target_subject_id,
        relationship_kind=relationship_kind,
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Relationship not found",
        ) from None


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


@router.patch("/{subject_id}", response_model=SubjectResponse)
@limit_writes
async def update_subject(
    request: Request,
    subject_id: str,
    body: SubjectUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: Annotated[SubjectService, Depends(get_subject_service)],
    _: Annotated[object, Depends(require_permission("subject", "update"))] = None,
):
    """Partial update (patch) of subject (e.g. external_ref, display_name, attributes). Tenant-scoped."""
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
