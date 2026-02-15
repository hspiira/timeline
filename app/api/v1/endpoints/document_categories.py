"""Document category configuration API: thin routes delegating to document category repository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_document_category_repo,
    get_document_category_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.interfaces.repositories import IDocumentCategoryRepository
from app.core.limiter import limit_writes
from app.schemas.document_category import (
    DocumentCategoryCreateRequest,
    DocumentCategoryListItem,
    DocumentCategoryResponse,
    DocumentCategoryUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=DocumentCategoryResponse, status_code=201)
@limit_writes
async def create_document_category(
    request: Request,
    body: DocumentCategoryCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        IDocumentCategoryRepository, Depends(get_document_category_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("document_category", "create"))
    ] = None,
):
    """Create a document category (tenant-scoped)."""
    try:
        created = await repo.create_document_category(
            tenant_id=tenant_id,
            category_name=body.category_name,
            display_name=body.display_name,
            description=body.description,
            metadata_schema=body.metadata_schema,
            default_retention_days=body.default_retention_days,
            is_active=body.is_active,
        )
        return DocumentCategoryResponse.model_validate(created)
    except Exception as e:
        if "uq_document_category_tenant_name" in str(e) or "UniqueViolation" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Document category with this category_name already exists for this tenant",
            ) from e
        raise


@router.get("", response_model=list[DocumentCategoryListItem])
async def list_document_categories(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[IDocumentCategoryRepository, Depends(get_document_category_repo)],
    _: Annotated[
        object, Depends(require_permission("document_category", "read"))
    ] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List document categories for the tenant."""
    items = await repo.get_by_tenant(tenant_id=tenant_id, skip=skip, limit=limit)
    return [
        DocumentCategoryListItem(
            id=c.id,
            tenant_id=c.tenant_id,
            category_name=c.category_name,
            display_name=c.display_name,
            description=c.description,
            default_retention_days=c.default_retention_days,
            is_active=c.is_active,
        )
        for c in items
    ]


@router.get("/{category_id}", response_model=DocumentCategoryResponse)
async def get_document_category(
    category_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[IDocumentCategoryRepository, Depends(get_document_category_repo)],
    _: Annotated[
        object, Depends(require_permission("document_category", "read"))
    ] = None,
):
    """Get document category by id (tenant-scoped)."""
    item = await repo.get_by_id(category_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document category not found")
    return DocumentCategoryResponse.model_validate(item)


@router.patch("/{category_id}", response_model=DocumentCategoryResponse)
@limit_writes
async def update_document_category(
    request: Request,
    category_id: str,
    body: DocumentCategoryUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        IDocumentCategoryRepository, Depends(get_document_category_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("document_category", "update"))
    ] = None,
):
    """Update document category (partial, tenant-scoped)."""
    item = await repo.get_by_id(category_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document category not found")
    updated = await repo.update_document_category(
        category_id,
        display_name=body.display_name,
        description=body.description,
        metadata_schema=body.metadata_schema,
        default_retention_days=body.default_retention_days,
        is_active=body.is_active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Document category not found")
    return DocumentCategoryResponse.model_validate(updated)


@router.delete("/{category_id}", status_code=204)
@limit_writes
async def delete_document_category(
    request: Request,
    category_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[
        IDocumentCategoryRepository, Depends(get_document_category_repo_for_write)
    ],
    _: Annotated[
        object, Depends(require_permission("document_category", "delete"))
    ] = None,
):
    """Delete document category (tenant-scoped)."""
    deleted = await repo.delete_document_category(category_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document category not found")
