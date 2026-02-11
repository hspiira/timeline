"""Document repository with audit. Returns application DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.document import DocumentResult
from app.infrastructure.persistence.models.document import Document
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction
from app.shared.utils import utc_now

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _result_to_document(d: DocumentResult) -> Document:
    """Map application DocumentResult to ORM Document (for create)."""
    return Document(
        id=d.id,
        tenant_id=d.tenant_id,
        subject_id=d.subject_id,
        event_id=d.event_id,
        document_type=d.document_type,
        filename=d.filename,
        original_filename=d.original_filename,
        mime_type=d.mime_type,
        file_size=d.file_size,
        checksum=d.checksum,
        storage_ref=d.storage_ref,
        version=d.version,
        parent_document_id=d.parent_document_id,
        is_latest_version=d.is_latest_version,
        created_by=d.created_by,
        deleted_at=d.deleted_at,
    )


def _document_to_result(d: Document) -> DocumentResult:
    """Map ORM Document to application DocumentResult."""
    return DocumentResult(
        id=d.id,
        tenant_id=d.tenant_id,
        subject_id=d.subject_id,
        event_id=d.event_id,
        document_type=d.document_type,
        filename=d.filename,
        original_filename=d.original_filename,
        mime_type=d.mime_type,
        file_size=d.file_size,
        checksum=d.checksum,
        storage_ref=d.storage_ref,
        version=d.version,
        parent_document_id=d.parent_document_id,
        is_latest_version=d.is_latest_version,
        created_by=d.created_by,
        deleted_at=d.deleted_at,
    )


class DocumentRepository(AuditableRepository[Document]):
    """Document repository. create() accepts DocumentResult or Document; returns DTO (LSP-safe input)."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Document, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "document"

    def _get_tenant_id(self, obj: Document) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: Document) -> dict[str, Any]:
        return {
            "id": obj.id,
            "filename": obj.filename,
            "original_filename": obj.original_filename,
            "mime_type": obj.mime_type,
            "file_size": obj.file_size,
            "subject_id": obj.subject_id,
            "event_id": obj.event_id,
            "version": obj.version,
        }

    def _should_audit(self, action: AuditAction, obj: Document) -> bool:
        """Skip UPDATED when document is soft-deleted so only DELETED is emitted."""
        if action == AuditAction.UPDATED and obj.deleted_at is not None:
            return False
        return super()._should_audit(action, obj)

    async def get_by_id(self, document_id: str) -> DocumentResult | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        row = result.scalar_one_or_none()
        return _document_to_result(row) if row else None

    async def _get_orm_by_id(self, document_id: str) -> Document | None:
        """Return ORM Document by id (for internal use by update)."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def _get_orm_by_id_and_tenant(
        self, document_id: str, tenant_id: str
    ) -> Document | None:
        """Return ORM Document by id and tenant_id (tenant-scoped lookup)."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: DocumentResult | Document) -> DocumentResult:
        """Create document from DTO or ORM; returns DTO. No dict (LSP: typed input only)."""
        orm = _result_to_document(obj) if isinstance(obj, DocumentResult) else obj
        created = await super().create(orm)
        return _document_to_result(created)

    async def mark_parent_not_latest_if_current(
        self, parent_id: str, expected_version: int
    ) -> bool:
        """Set is_latest_version=False only if document is still current (optimistic lock).

        Returns True if exactly one row was updated; False if another request won the race.
        """
        stmt = (
            update(Document)
            .where(
                Document.id == parent_id,
                Document.is_latest_version.is_(True),
                Document.version == expected_version,
            )
            .values(is_latest_version=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount == 1

    async def update(self, document: DocumentResult) -> DocumentResult:
        """Update document from DTO (e.g. is_latest_version, document_type); return updated DTO."""
        orm = await self._get_orm_by_id(document.id)
        if not orm:
            raise ValueError(f"Document {document.id} not found")
        orm.is_latest_version = document.is_latest_version
        orm.deleted_at = document.deleted_at
        orm.document_type = document.document_type
        updated = await super().update(orm)
        return _document_to_result(updated)

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[DocumentResult]:
        q = select(Document).where(
            and_(Document.subject_id == subject_id, Document.tenant_id == tenant_id)
        )
        if not include_deleted:
            q = q.where(Document.deleted_at.is_(None))
        q = q.order_by(Document.created_at.desc())
        result = await self.db.execute(q)
        return [_document_to_result(d) for d in result.scalars().all()]

    async def get_by_event(
        self, event_id: str, tenant_id: str
    ) -> list[DocumentResult]:
        """Return documents linked to an event (tenant-scoped, exclude deleted)."""
        result = await self.db.execute(
            select(Document)
            .where(
                and_(
                    Document.event_id == event_id,
                    Document.tenant_id == tenant_id,
                    Document.deleted_at.is_(None),
                )
            )
            .order_by(Document.created_at.desc())
        )
        return [_document_to_result(d) for d in result.scalars().all()]

    async def get_versions(
        self, document_id: str, tenant_id: str
    ) -> list[DocumentResult]:
        """Return this document plus all documents with parent_document_id = document_id (version chain)."""
        doc = await self.get_by_id(document_id)
        if not doc or doc.tenant_id != tenant_id:
            return []
        result = await self.db.execute(
            select(Document)
            .where(
                and_(
                    Document.parent_document_id == document_id,
                    Document.tenant_id == tenant_id,
                )
            )
            .order_by(Document.version.asc())
        )
        children = [_document_to_result(d) for d in result.scalars().all()]
        return [doc] + children

    async def get_by_checksum(
        self, tenant_id: str, checksum: str
    ) -> DocumentResult | None:
        result = await self.db.execute(
            select(Document).where(
                and_(
                    Document.tenant_id == tenant_id,
                    Document.checksum == checksum,
                    Document.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        return _document_to_result(row) if row else None

    async def soft_delete(
        self, document_id: str, tenant_id: str
    ) -> DocumentResult | None:
        """Soft-delete document by id; returns None if not found in tenant."""
        orm = await self._get_orm_by_id_and_tenant(document_id, tenant_id)
        if not orm:
            return None
        orm.deleted_at = utc_now()
        updated = await super().update(orm)
        await self.emit_custom_audit(updated, AuditAction.DELETED)
        return _document_to_result(updated)
