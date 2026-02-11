"""Document operations: upload (write) and query (read) with single responsibilities."""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import timedelta
from typing import BinaryIO

from app.application.dtos.document import (
    DocumentCreate,
    DocumentListItem,
    DocumentMetadata,
    DocumentResult,
)
from app.application.interfaces.repositories import (
    IDocumentRepository,
    ITenantRepository,
)
from app.application.interfaces.storage import IStorageService
from app.domain.exceptions import (
    DocumentVersionConflictException,
    ResourceNotFoundException,
    ValidationException,
)
from app.shared.utils.generators import generate_cuid


def _rewind_if_seekable(file_data: BinaryIO) -> None:
    """Reset file position to start if stream is seekable."""
    if getattr(file_data, "seekable", lambda: False)() and file_data.seekable():
        file_data.seek(0)


def _sanitize_filename(filename: str) -> str:
    """Strip path separators and dangerous characters from filename."""
    name = os.path.basename(filename)
    name = name.replace("\x00", "").strip(". ")
    if not name:
        raise ValueError("Filename is empty or invalid after sanitization")
    return name


def _compute_checksum_and_size_sync(file_data: BinaryIO) -> tuple[str, int]:
    """Blocking: one pass over file_data (run in executor). Returns (hexdigest, byte_count)."""
    sha256 = hashlib.sha256()
    total = 0
    while chunk := file_data.read(65536):
        sha256.update(chunk)
        total += len(chunk)
    _rewind_if_seekable(file_data)
    return sha256.hexdigest(), total


class DocumentUploadService:
    """Single responsibility: upload document to storage and create document record."""

    def __init__(
        self,
        storage_service: IStorageService,
        document_repo: IDocumentRepository,
        tenant_repo: ITenantRepository,
    ) -> None:
        self.storage = storage_service
        self.document_repo = document_repo
        self.tenant_repo = tenant_repo

    def _generate_storage_ref(
        self,
        tenant_code: str,
        document_id: str,
        version: int,
        filename: str,
    ) -> str:
        safe = _sanitize_filename(filename)
        return f"tenants/{tenant_code}/documents/{document_id}/v{version}/{safe}"

    async def _compute_checksum_and_size(
        self, file_data: BinaryIO
    ) -> tuple[str, int]:
        return await asyncio.to_thread(
            _compute_checksum_and_size_sync, file_data
        )

    async def upload_document(
        self,
        tenant_id: str,
        subject_id: str,
        file_data: BinaryIO,
        filename: str,
        original_filename: str,
        mime_type: str,
        document_type: str,
        event_id: str | None = None,
        created_by: str | None = None,
        parent_document_id: str | None = None,
    ) -> DocumentResult:
        """Upload file to storage and create document record. Returns created document."""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundException("tenant", tenant_id)

        checksum, file_size = await self._compute_checksum_and_size(file_data)
        _rewind_if_seekable(file_data)

        existing = await self.document_repo.get_by_checksum(tenant_id, checksum)
        if existing:
            raise ValidationException("Duplicate document checksum", field="checksum")

        version = 1
        if parent_document_id:
            parent = await self.document_repo.get_by_id_and_tenant(
                parent_document_id, tenant_id
            )
            if not parent:
                raise ResourceNotFoundException("document", parent_document_id)
            version = parent.version + 1
            updated = await self.document_repo.mark_parent_not_latest_if_current(
                parent_document_id, parent.version
            )
            if not updated:
                raise DocumentVersionConflictException(parent_document_id)

        document_id = generate_cuid()
        tenant_code = tenant.code
        storage_ref = self._generate_storage_ref(
            tenant_code, document_id, version, filename
        )
        _rewind_if_seekable(file_data)

        await self.storage.upload(
            file_data=file_data,
            storage_ref=storage_ref,
            expected_checksum=checksum,
            content_type=mime_type,
            metadata={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "subject_id": subject_id,
            },
        )

        create_dto = DocumentCreate(
            id=document_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
            event_id=event_id,
            document_type=document_type,
            filename=filename,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size=file_size,
            checksum=checksum,
            storage_ref=storage_ref,
            version=version,
            parent_document_id=parent_document_id,
            created_by=created_by,
        )
        return await self.document_repo.create(create_dto)


class DocumentQueryService:
    """Single responsibility: document metadata, download URL, and listing."""

    def __init__(
        self,
        storage_service: IStorageService,
        document_repo: IDocumentRepository,
    ) -> None:
        self.storage = storage_service
        self.document_repo = document_repo

    async def get_document_metadata(
        self, tenant_id: str, document_id: str
    ) -> DocumentMetadata:
        """Return document metadata; raise ResourceNotFoundException if not found or wrong tenant."""
        doc = await self.document_repo.get_by_id_and_tenant(document_id, tenant_id)
        if not doc:
            raise ResourceNotFoundException("document", document_id)
        return DocumentMetadata(
            id=doc.id,
            tenant_id=doc.tenant_id,
            subject_id=doc.subject_id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            version=doc.version,
            storage_ref=doc.storage_ref,
        )

    async def get_download_url(
        self,
        tenant_id: str,
        document_id: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> str:
        """Return temporary download URL; raise ResourceNotFoundException if not found or wrong tenant."""
        doc = await self.document_repo.get_by_id_and_tenant(document_id, tenant_id)
        if not doc:
            raise ResourceNotFoundException("document", document_id)
        if not doc.storage_ref:
            raise ResourceNotFoundException("document", document_id)
        return await self.storage.generate_download_url(
            doc.storage_ref, expiration=expiration
        )

    async def list_documents(
        self, tenant_id: str, subject_id: str
    ) -> list[DocumentListItem]:
        """Return documents for subject in tenant (metadata only)."""
        docs = await self.document_repo.get_by_subject(
            subject_id=subject_id,
            tenant_id=tenant_id,
            include_deleted=False,
        )
        return [
            DocumentListItem(
                id=d.id,
                filename=d.filename,
                mime_type=d.mime_type,
                file_size=d.file_size,
                version=d.version,
            )
            for d in docs
        ]
