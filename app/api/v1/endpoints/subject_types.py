"""Subject type configuration API: thin routes delegating to subject type repository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_subject_type_repo,
    get_subject_type_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.dtos.user import UserResult
from app.application.interfaces.repositories import ISubjectTypeRepository
from app.core.limiter import limit_writes
from app.schemas.subject_type import (
    SubjectTypeCreateRequest,
    SubjectTypeListItem,
    SubjectTypeResponse,
    SubjectTypeUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=SubjectTypeResponse, status_code=201)
@limit_writes
async def create_subject_type(
    request: Request,
    body: SubjectTypeCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(require_permission("subject_type", "create"))],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo_for_write)],
):
    """Create a subject type (tenant-scoped). created_by from authenticated user."""
    try:
        created = await repo.create_subject_type(
            tenant_id=tenant_id,
            type_name=body.type_name,
            display_name=body.display_name,
            description=body.description,
            schema=body.schema_definition,
            is_active=body.is_active,
            icon=body.icon,
            color=body.color,
            has_timeline=body.has_timeline,
            allow_documents=body.allow_documents,
            allowed_event_types=body.allowed_event_types,
            created_by=current_user.id,
        )
        return SubjectTypeResponse(
            id=created.id,
            tenant_id=created.tenant_id,
            type_name=created.type_name,
            display_name=created.display_name,
            description=created.description,
            schema_definition=created.schema,
            version=created.version,
            is_active=created.is_active,
            icon=created.icon,
            color=created.color,
            has_timeline=created.has_timeline,
            allow_documents=created.allow_documents,
            allowed_event_types=created.allowed_event_types,
            created_by=created.created_by,
        )
    except Exception as e:
        if "uq_subject_type_tenant_type" in str(e) or "UniqueViolation" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Subject type with this type_name already exists for this tenant",
            ) from e
        raise


@router.get("", response_model=list[SubjectTypeListItem])
async def list_subject_types(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo)],
    _: Annotated[object, Depends(require_permission("subject_type", "read"))] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List subject types for the tenant."""
    items = await repo.get_by_tenant(tenant_id=tenant_id, skip=skip, limit=limit)
    return [
        SubjectTypeListItem(
            id=s.id,
            tenant_id=s.tenant_id,
            type_name=s.type_name,
            display_name=s.display_name,
            description=s.description,
            version=s.version,
            is_active=s.is_active,
            icon=s.icon,
            color=s.color,
            has_timeline=s.has_timeline,
            allow_documents=s.allow_documents,
            allowed_event_types=s.allowed_event_types,
        )
        for s in items
    ]


@router.get("/{subject_type_id}", response_model=SubjectTypeResponse)
async def get_subject_type(
    subject_type_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo)],
    _: Annotated[object, Depends(require_permission("subject_type", "read"))] = None,
):
    """Get subject type by id (must belong to tenant)."""
    item = await repo.get_by_id(subject_type_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Subject type not found")
    return SubjectTypeResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        type_name=item.type_name,
        display_name=item.display_name,
        description=item.description,
        schema_definition=item.schema,
        version=item.version,
        is_active=item.is_active,
        icon=item.icon,
        color=item.color,
        has_timeline=item.has_timeline,
        allow_documents=item.allow_documents,
        allowed_event_types=item.allowed_event_types,
        created_by=item.created_by,
    )


@router.patch("/{subject_type_id}", response_model=SubjectTypeResponse)
@limit_writes
async def update_subject_type(
    request: Request,
    subject_type_id: str,
    body: SubjectTypeUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo_for_write)],
    _: Annotated[object, Depends(require_permission("subject_type", "update"))] = None,
):
    """Update subject type (partial)."""
    item = await repo.get_by_id(subject_type_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Subject type not found")
    updated = await repo.update_subject_type(
        subject_type_id,
        display_name=body.display_name,
        description=body.description,
        schema=body.schema_definition,
        is_active=body.is_active,
        icon=body.icon,
        color=body.color,
        has_timeline=body.has_timeline,
        allow_documents=body.allow_documents,
        allowed_event_types=body.allowed_event_types,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Subject type not found")
    return SubjectTypeResponse(
        id=updated.id,
        tenant_id=updated.tenant_id,
        type_name=updated.type_name,
        display_name=updated.display_name,
        description=updated.description,
        schema_definition=updated.schema,
        version=updated.version,
        is_active=updated.is_active,
        icon=updated.icon,
        color=updated.color,
        has_timeline=updated.has_timeline,
        allow_documents=updated.allow_documents,
        allowed_event_types=updated.allowed_event_types,
        created_by=updated.created_by,
    )


@router.delete("/{subject_type_id}", status_code=204)
@limit_writes
async def delete_subject_type(
    request: Request,
    subject_type_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo_for_write)],
    _: Annotated[object, Depends(require_permission("subject_type", "delete"))] = None,
):
    """Delete subject type (tenant-scoped)."""
    deleted = await repo.delete_subject_type(subject_type_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subject type not found")
