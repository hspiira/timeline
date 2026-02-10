"""Subject API: thin routes delegating to SubjectService and SubjectRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_subject_repo_for_write,
    get_subject_service,
    get_tenant_id,
)
from app.application.use_cases.subjects import SubjectService
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.schemas.subject import SubjectCreateRequest, SubjectResponse, SubjectUpdate

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


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    body: SubjectUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_repo: SubjectRepository = Depends(get_subject_repo_for_write),
):
    """Update subject (e.g. external_ref). Tenant-scoped."""
    subject = await subject_repo.get_entity_by_id_and_tenant(subject_id, tenant_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if body.external_ref is not None:
        subject.external_ref = body.external_ref
    updated = await subject_repo.update(subject)
    return SubjectResponse(
        id=updated.id,
        tenant_id=updated.tenant_id,
        subject_type=updated.subject_type,
        external_ref=updated.external_ref,
    )


@router.delete("/{subject_id}", status_code=204)
async def delete_subject(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_repo: SubjectRepository = Depends(get_subject_repo_for_write),
):
    """Delete subject. Tenant-scoped."""
    subject = await subject_repo.get_entity_by_id_and_tenant(subject_id, tenant_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await subject_repo.delete(subject)
