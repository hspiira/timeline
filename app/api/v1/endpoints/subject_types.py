"""Subject type configuration API: thin routes delegating to subject type repository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import (
    ensure_audit_logged,
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
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
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
        return SubjectTypeResponse.model_validate(created)
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail="Subject type with this type_name already exists for this tenant",
        ) from e


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
    return [SubjectTypeListItem.model_validate(s) for s in items]


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
    return SubjectTypeResponse.model_validate(item)


@router.patch("/{subject_type_id}", response_model=SubjectTypeResponse)
@limit_writes
async def update_subject_type(
    request: Request,
    subject_type_id: str,
    body: SubjectTypeUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo_for_write)],
    _: Annotated[object, Depends(require_permission("subject_type", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Update subject type (partial). Only provided fields are updated; explicit null clears optional fields."""
    item = await repo.get_by_id(subject_type_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Subject type not found")
    # Build kwargs only for fields present in the request (model_fields_set); allows clearing with null.
    updates: dict[str, object] = {}
    if "display_name" in body.model_fields_set:
        updates["display_name"] = body.display_name
    if "description" in body.model_fields_set:
        updates["description"] = body.description
    if "schema_definition" in body.model_fields_set:
        updates["schema"] = body.schema_definition
    if "is_active" in body.model_fields_set:
        updates["is_active"] = body.is_active
    if "icon" in body.model_fields_set:
        updates["icon"] = body.icon
    if "color" in body.model_fields_set:
        updates["color"] = body.color
    if "has_timeline" in body.model_fields_set:
        updates["has_timeline"] = body.has_timeline
    if "allow_documents" in body.model_fields_set:
        updates["allow_documents"] = body.allow_documents
    if "allowed_event_types" in body.model_fields_set:
        updates["allowed_event_types"] = body.allowed_event_types
    updated = await repo.update_subject_type(subject_type_id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Subject type not found")
    return SubjectTypeResponse.model_validate(updated)


@router.delete("/{subject_type_id}", status_code=204)
@limit_writes
async def delete_subject_type(
    request: Request,
    subject_type_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[ISubjectTypeRepository, Depends(get_subject_type_repo_for_write)],
    _: Annotated[object, Depends(require_permission("subject_type", "delete"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Delete subject type (tenant-scoped)."""
    deleted = await repo.delete_subject_type(subject_type_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subject type not found")
