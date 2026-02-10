"""Document operations: upload/download and read coordinating storage and document repo."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any, BinaryIO

from app.application.interfaces.repositories import (
    IDocumentRepository,
    ITenantRepository,
)
from app.application.interfaces.storage import IStorageService
from app.domain.exceptions import ResourceNotFoundException
from app.shared.utils.generators import generate_cuid


class DocumentService:
    """Orchestrates document upload/download (storage + document repo + tenant repo)."""

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
        return f"tenants/{tenant_code}/documents/{document_id}/v{version}/{filename}"

    async def _compute_checksum(self, file_data: BinaryIO) -> str:
        sha256 = hashlib.sha256()
        content = file_data.read()
        sha256.update(content)
        file_data.seek(0)
        return sha256.hexdigest()

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
    ) -> Any:
        """Upload file to storage and create document record. Returns created document."""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundException("tenant", tenant_id)

        file_data.seek(0)
        checksum = await self._compute_checksum(file_data)
        file_data.seek(0)

        existing = await self.document_repo.get_by_checksum(tenant_id, checksum)
        if existing:
            raise ValueError(
                f"Document with checksum {checksum} already exists (ID: {existing.id})"
            )

        version = 1
        if parent_document_id:
            parent = await self.document_repo.get_by_id(parent_document_id)
            if not parent:
                raise ResourceNotFoundException("document", parent_document_id)
            if getattr(parent, "tenant_id", None) != tenant_id:
                raise ValueError("Parent document belongs to different tenant")
            version = getattr(parent, "version", 0) + 1
            parent.is_latest_version = False
            await self.document_repo.update(parent)

        document_id = generate_cuid()
        tenant_code = getattr(tenant, "code", tenant_id)
        storage_ref = self._generate_storage_ref(
            tenant_code, document_id, version, filename
        )

        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)

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

        document_dto = {
            "id": document_id,
            "tenant_id": tenant_id,
            "subject_id": subject_id,
            "event_id": event_id,
            "document_type": document_type,
            "filename": filename,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "checksum": checksum,
            "storage_ref": storage_ref,
            "version": version,
            "is_latest_version": True,
            "parent_document_id": parent_document_id,
            "created_by": created_by,
        }
        return await self.document_repo.create(document_dto)

    async def get_document_metadata(
        self, tenant_id: str, document_id: str
    ) -> dict[str, Any]:
        """Return document metadata; raise ResourceNotFoundException if not found or wrong tenant."""
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise ResourceNotFoundException("document", document_id)
        if getattr(doc, "tenant_id", None) != tenant_id:
            raise ResourceNotFoundException("document", document_id)
        return {
            "id": getattr(doc, "id", None),
            "tenant_id": getattr(doc, "tenant_id", None),
            "subject_id": getattr(doc, "subject_id", None),
            "filename": getattr(doc, "filename", None),
            "original_filename": getattr(doc, "original_filename", None),
            "mime_type": getattr(doc, "mime_type", None),
            "file_size": getattr(doc, "file_size", None),
            "version": getattr(doc, "version", None),
            "storage_ref": getattr(doc, "storage_ref", None),
        }

    async def get_download_url(
        self,
        tenant_id: str,
        document_id: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> str:
        """Return temporary download URL; raise ResourceNotFoundException if not found or wrong tenant."""
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise ResourceNotFoundException("document", document_id)
        if getattr(doc, "tenant_id", None) != tenant_id:
            raise ResourceNotFoundException("document", document_id)
        storage_ref = getattr(doc, "storage_ref", None)
        if not storage_ref:
            raise ResourceNotFoundException("document", document_id)
        return await self.storage.generate_download_url(
            storage_ref, expiration=expiration
        )

    async def list_documents(
        self, tenant_id: str, subject_id: str
    ) -> list[dict[str, Any]]:
        """Return documents for subject in tenant (metadata only)."""
        docs = await self.document_repo.get_by_subject(
            subject_id=subject_id,
            tenant_id=tenant_id,
            include_deleted=False,
        )
        return [
            {
                "id": getattr(d, "id", None),
                "filename": getattr(d, "filename", None),
                "mime_type": getattr(d, "mime_type", None),
                "file_size": getattr(d, "file_size", None),
                "version": getattr(d, "version", None),
            }
            for d in docs
        ]
