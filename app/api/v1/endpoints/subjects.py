"""Subject API: thin routes delegating to SubjectService."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_subject_service
from app.application.use_cases.subjects import SubjectService
from app.core.config import get_settings
from app.domain.exceptions import ResourceNotFoundException
from app.schemas.subject import SubjectCreateRequest, SubjectResponse

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {name}",
        )
    return x_tenant_id


@router.post("", response_model=SubjectResponse, status_code=201)
async def create_subject(
    body: SubjectCreateRequest,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    subject_svc: SubjectService = Depends(get_subject_service),
):
    """Create a subject (tenant-scoped)."""
    created = await subject_svc.create_subject(
        tenant_id=tenant_id,
        subject_type=body.subject_type,
        external_ref=body.external_ref,
    )
    return SubjectResponse(
        id=created.id,
        tenant_id=created.tenant_id,
        subject_type=created.subject_type,
        external_ref=created.external_ref,
    )


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    subject_svc: SubjectService = Depends(get_subject_service),
):
    """Get subject by id (tenant-scoped)."""
    try:
        subject = await subject_svc.get_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
        )
        return SubjectResponse(
            id=subject.id,
            tenant_id=subject.tenant_id,
            subject_type=subject.subject_type,
            external_ref=subject.external_ref,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Subject not found")


@router.get("")
async def list_subjects(
    tenant_id: Annotated[str, Depends(_tenant_id)],
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
    return [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "subject_type": s.subject_type,
            "external_ref": s.external_ref,
        }
        for s in subjects
    ]
