"""Document API: thin routes delegating to DocumentService and DocumentRepository."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.v1.dependencies import (
    get_document_repo,
    get_document_repo_for_write,
    get_document_service,
    get_tenant_id,
)
from app.application.use_cases.documents import DocumentService
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.repositories.document_repo import (
    DocumentRepository,
)
from app.schemas.document import DocumentUpdate

router = APIRouter()


@router.post("", status_code=201)
async def upload_document(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    event_id: str | None = Form(None),
    created_by: str | None = Form(None),
    parent_document_id: str | None = Form(None),
    doc_svc: DocumentService = Depends(get_document_service),
):
    """Upload a document for a subject (storage + document record)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    content_type = file.content_type or "application/octet-stream"
    try:
        created = await doc_svc.upload_document(
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
        return {"id": created.id, "filename": file.filename}
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("")
async def list_documents(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    subject_id: str,
    doc_svc: DocumentService = Depends(get_document_service),
):
    """List documents for a subject (tenant-scoped). subject_id is required."""
    items = await doc_svc.list_documents(tenant_id=tenant_id, subject_id=subject_id)
    return items


@router.get("/event/{event_id}")
async def list_documents_by_event(
    event_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """List documents linked to an event (tenant-scoped)."""
    docs = await document_repo.get_by_event(event_id=event_id, tenant_id=tenant_id)
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "mime_type": d.mime_type,
            "file_size": d.file_size,
            "version": d.version,
        }
        for d in docs
    ]


@router.get("/{document_id}/versions")
async def get_document_versions(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Get this document and its version chain (tenant-scoped)."""
    doc = await document_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    versions = await document_repo.get_versions(document_id, tenant_id)
    return [
        {
            "id": d.id,
            "tenant_id": d.tenant_id,
            "subject_id": d.subject_id,
            "filename": d.filename,
            "mime_type": d.mime_type,
            "file_size": d.file_size,
            "version": d.version,
        }
        for d in versions
    ]


@router.get("/{document_id}/download-url")
async def get_document_download_url(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    expires_in_hours: int = 1,
    doc_svc: DocumentService = Depends(get_document_service),
):
    """Get temporary download URL for document (tenant-scoped). Defined before /{document_id} for route precedence."""
    try:
        url = await doc_svc.get_download_url(
            tenant_id=tenant_id,
            document_id=document_id,
            expiration=timedelta(hours=expires_in_hours),
        )
        return {"url": url, "expires_in_hours": expires_in_hours}
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail="Document not found") from e


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    doc_svc: DocumentService = Depends(get_document_service),
):
    """Get document metadata by id (tenant-scoped)."""
    try:
        meta = await doc_svc.get_document_metadata(
            tenant_id=tenant_id,
            document_id=document_id,
        )
        return meta
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail="Document not found") from e


@router.put("/{document_id}")
async def update_document(
    document_id: str,
    body: DocumentUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo_for_write),
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
    return {
        "id": updated.id,
        "tenant_id": updated.tenant_id,
        "subject_id": updated.subject_id,
        "filename": updated.filename,
        "mime_type": updated.mime_type,
        "file_size": updated.file_size,
        "version": updated.version,
    }


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_repo: DocumentRepository = Depends(get_document_repo_for_write),
):
    """Soft-delete document. Tenant-scoped."""
    doc = await document_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.deleted_at:
        raise HTTPException(status_code=410, detail="Document already deleted")
    await document_repo.soft_delete(document_id, tenant_id)
