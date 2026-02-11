"""Document API: thin routes delegating to DocumentUploadService, DocumentQueryService, and DocumentRepository."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile

from app.api.v1.dependencies import (
    get_document_query_service,
    get_document_repo,
    get_document_repo_for_write,
    get_document_upload_service,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.documents import (
    DocumentQueryService,
    DocumentUploadService,
)
from app.core.limiter import limit_writes
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.repositories.document_repo import (
    DocumentRepository,
)
from app.schemas.document import (
    DocumentDownloadUrlResponse,
    DocumentListItem,
    DocumentUpdate,
    DocumentUploadResponse,
    DocumentVersionItem,
)

router = APIRouter()


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=201,
)
@limit_writes
async def upload_document(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    event_id: str | None = Form(None),
    created_by: str | None = Form(None),
    parent_document_id: str | None = Form(None),
    upload_svc: DocumentUploadService = Depends(get_document_upload_service),
    _: Annotated[object, Depends(require_permission("document", "create"))] = None,
):
    """Upload a document for a subject (storage + document record)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    content_type = file.content_type or "application/octet-stream"
    try:
        created = await upload_svc.upload_document(
            tenant_id=tenant_id,
            subject_id=subject_id,
            file_data=file.file,
            filename=file.filename,
            original_filename=file.filename,
            mime_type=content_type,
            document_type=document_type,
            event_id=event_id,
            created_by=created_by,
            parent_document_id=parent_document_id,
        )
        return DocumentUploadResponse(id=created.id, filename=file.filename)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[DocumentListItem])
async def list_documents(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_id: str,
    query_svc: DocumentQueryService = Depends(get_document_query_service),
    _: Annotated[object, Depends(require_permission("document", "read"))] = None,
):
    """List documents for a subject (tenant-scoped). subject_id is required."""
    items = await query_svc.list_documents(tenant_id=tenant_id, subject_id=subject_id)
    return [DocumentListItem.model_validate(i) for i in items]


@router.get(
    "/event/{event_id}",
    response_model=list[DocumentListItem],
)
async def list_documents_by_event(
    event_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo),
    _: Annotated[object, Depends(require_permission("document", "read"))] = None,
):
    """List documents linked to an event (tenant-scoped)."""
    docs = await document_repo.get_by_event(event_id=event_id, tenant_id=tenant_id)
    return [DocumentListItem.model_validate(d) for d in docs]


@router.get(
    "/{document_id}/versions",
    response_model=list[DocumentVersionItem],
)
async def get_document_versions(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo),
    _: Annotated[object, Depends(require_permission("document", "read"))] = None,
):
    """Get this document and its version chain (tenant-scoped)."""
    doc = await document_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    versions = await document_repo.get_versions(document_id, tenant_id)
    return [DocumentVersionItem.model_validate(d) for d in versions]


@router.get(
    "/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
)
async def get_document_download_url(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    expires_in_hours: int = Query(1, ge=1, le=168),
    query_svc: DocumentQueryService = Depends(get_document_query_service),
    _: Annotated[object, Depends(require_permission("document", "read"))] = None,
):
    """Get temporary download URL for document (tenant-scoped). Defined before /{document_id} for route precedence."""
    try:
        url = await query_svc.get_download_url(
            tenant_id=tenant_id,
            document_id=document_id,
            expiration=timedelta(hours=expires_in_hours),
        )
        return DocumentDownloadUrlResponse(
            url=url, expires_in_hours=expires_in_hours
        )
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail="Document not found") from e


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    query_svc: DocumentQueryService = Depends(get_document_query_service),
    _: Annotated[object, Depends(require_permission("document", "read"))] = None,
):
    """Get document metadata by id (tenant-scoped)."""
    try:
        meta = await query_svc.get_document_metadata(
            tenant_id=tenant_id,
            document_id=document_id,
        )
        return meta
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail="Document not found") from e


@router.put("/{document_id}", response_model=DocumentVersionItem)
@limit_writes
async def update_document(
    request: Request,
    document_id: str,
    body: DocumentUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo_for_write),
    _: Annotated[object, Depends(require_permission("document", "update"))] = None,
):
    """Update document metadata (e.g. document_type). Tenant-scoped."""
    doc = await document_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.deleted_at:
        raise HTTPException(status_code=410, detail="Document has been deleted")
    if body.document_type is not None:
        doc.document_type = body.document_type
    updated = await document_repo.update(doc)
    return DocumentVersionItem.model_validate(updated)


@router.delete("/{document_id}", status_code=204)
@limit_writes
async def delete_document(
    request: Request,
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo_for_write),
    _: Annotated[object, Depends(require_permission("document", "delete"))] = None,
):
    """Soft-delete document. Tenant-scoped."""
    doc = await document_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.deleted_at:
        raise HTTPException(status_code=410, detail="Document already deleted")
    await document_repo.soft_delete(document_id, tenant_id)
