"""Subject API: thin routes delegating to SubjectService."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_subject_service, get_tenant_id
from app.application.use_cases.subjects import SubjectService
from app.domain.exceptions import ResourceNotFoundException
from app.schemas.subject import SubjectCreateRequest, SubjectResponse

router = APIRouter()


@router.post("", response_model=SubjectResponse, status_code=201)
async def create_subject(
    body: SubjectCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_svc: SubjectService = Depends(get_subject_service),
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
    subject_svc: SubjectService = Depends(get_subject_service),
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
    skip: int = 0,
    limit: int = 100,
    subject_type: str | None = None,
    subject_svc: SubjectService = Depends(get_subject_service),
    ):
    """List subjects for tenant (optional type filter)."""
    subjects = await subject_svc.list_subjects(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        subject_type=subject_type,
    )
    return [SubjectResponse.model_validate(s) for s in subjects]
