"""Document API: thin routes delegating to DocumentService."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app.api.v1.dependencies import get_document_service
from app.application.use_cases.documents import DocumentService
from app.core.config import get_settings
from app.domain.exceptions import ResourceNotFoundException

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


@router.post("", status_code=201)
async def upload_document(
    tenant_id: Annotated[str, Depends(_tenant_id)],
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
        return {"id": getattr(created, "id", created), "filename": file.filename}
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_documents(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    subject_id: str,
    doc_svc: DocumentService = Depends(get_document_service),
):
    """List documents for a subject (tenant-scoped). subject_id is required."""
    items = await doc_svc.list_documents(tenant_id=tenant_id, subject_id=subject_id)
    return items


@router.get("/{document_id}/download-url")
async def get_document_download_url(
    document_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    expires_in_hours: int = 1,
    doc_svc: DocumentService = Depends(get_document_service),
):
    """Get temporary download URL for document (tenant-scoped). Defined before /{document_id} for route precedence."""
    from datetime import timedelta

    try:
        url = await doc_svc.get_download_url(
            tenant_id=tenant_id,
            document_id=document_id,
            expiration=timedelta(hours=expires_in_hours),
        )
        return {"url": url, "expires_in_hours": expires_in_hours}
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    doc_svc: DocumentService = Depends(get_document_service),
):
    """Get document metadata by id (tenant-scoped)."""
    try:
        meta = await doc_svc.get_document_metadata(
            tenant_id=tenant_id,
            document_id=document_id,
        )
        return meta
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Document not found")
