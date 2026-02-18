"""Relationship kind API: list, create, get, update, delete (tenant-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    get_relationship_kind_repo,
    get_relationship_kind_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.dtos.user import UserResult
from app.application.interfaces.repositories import IRelationshipKindRepository
from app.core.limiter import limit_writes
from app.domain.exceptions import ValidationException
from app.schemas.relationship_kind import (
    RelationshipKindCreateRequest,
    RelationshipKindListItem,
    RelationshipKindResponse,
    RelationshipKindUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=list[RelationshipKindListItem])
async def list_relationship_kinds(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[IRelationshipKindRepository, Depends(get_relationship_kind_repo)],
    _: Annotated[
        object, Depends(require_permission("relationship_kind", "read"))
    ] = None,
):
    """List relationship kinds for the tenant."""
    items = await repo.list_by_tenant(tenant_id=tenant_id)
    return [RelationshipKindListItem.model_validate(r) for r in items]


@router.post("", response_model=RelationshipKindResponse, status_code=201)
@limit_writes
async def create_relationship_kind(
    request: Request,
    body: RelationshipKindCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        IRelationshipKindRepository, Depends(get_relationship_kind_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("relationship_kind", "create"))
    ] = None,
):
    """Create a relationship kind (tenant-scoped)."""
    try:
        created = await repo.create(
            tenant_id=tenant_id,
            kind=body.kind,
            display_name=body.display_name,
            description=body.description,
            payload_schema=body.payload_schema,
        )
        return RelationshipKindResponse.model_validate(created)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message) from e


@router.get("/{kind_id}", response_model=RelationshipKindResponse)
async def get_relationship_kind(
    kind_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[IRelationshipKindRepository, Depends(get_relationship_kind_repo)],
    _: Annotated[
        object, Depends(require_permission("relationship_kind", "read"))
    ] = None,
):
    """Get relationship kind by id (must belong to tenant)."""
    item = await repo.get_by_id(kind_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Relationship kind not found")
    return RelationshipKindResponse.model_validate(item)


@router.patch("/{kind_id}", response_model=RelationshipKindResponse)
@limit_writes
async def update_relationship_kind(
    request: Request,
    kind_id: str,
    body: RelationshipKindUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        IRelationshipKindRepository, Depends(get_relationship_kind_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("relationship_kind", "update"))
    ] = None,
):
    """Update relationship kind (partial)."""
    updated = await repo.update(
        kind_id=kind_id,
        tenant_id=tenant_id,
        display_name=body.display_name,
        description=body.description,
        payload_schema=body.payload_schema,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Relationship kind not found")
    return RelationshipKindResponse.model_validate(updated)


@router.delete("/{kind_id}", status_code=204)
@limit_writes
async def delete_relationship_kind(
    request: Request,
    kind_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        IRelationshipKindRepository, Depends(get_relationship_kind_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("relationship_kind", "delete"))
    ] = None,
):
    """Delete relationship kind (tenant-scoped)."""
    deleted = await repo.delete(kind_id=kind_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship kind not found")
