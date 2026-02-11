"""Subject API: thin routes delegating to SubjectService."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_subject_service,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.subjects import SubjectService
from app.core.limiter import limit_writes
from app.domain.exceptions import ResourceNotFoundException
from app.schemas.subject import SubjectCreateRequest, SubjectResponse, SubjectUpdate

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
    )
    return SubjectResponse.model_validate(created)


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
    """Update subject (e.g. external_ref). Tenant-scoped."""
    try:
        updated = await subject_svc.update_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
            external_ref=body.external_ref,
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
