"""Document repository with audit. Returns application DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.document import DocumentCreate, DocumentResult
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.models.document import Document
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.shared.enums import AuditAction
from app.shared.utils import utc_now

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _create_to_document(d: DocumentCreate) -> Document:
    """Map DocumentCreate (write-model) to ORM Document for persistence."""
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
        is_latest_version=True,
        created_by=d.created_by,
        deleted_at=None,
        metadata_=d.metadata if d.metadata is not None else {},
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
        metadata=getattr(d, "metadata_", None),
    )


class DocumentRepository(AuditableRepository[Document]):
    """Document repository. create() accepts DocumentCreate (write-model); returns DocumentResult (read-model)."""

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

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return count of non-deleted documents for tenant."""
        result = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == tenant_id,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

    async def get_by_id(self, document_id: str) -> DocumentResult | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        row = result.scalar_one_or_none()
        return _document_to_result(row) if row else None

    async def get_by_id_and_tenant(
        self, document_id: str, tenant_id: str
    ) -> DocumentResult | None:
        """Return document by ID if it belongs to the tenant; otherwise None."""
        orm = await self._get_orm_by_id_and_tenant(document_id, tenant_id)
        return _document_to_result(orm) if orm else None

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

    async def create_document(self, document: DocumentCreate) -> DocumentResult:
        """Create document from write-model DTO; return read-model."""
        orm = _create_to_document(document)
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
            raise ResourceNotFoundException("document", document.id)
        orm.is_latest_version = document.is_latest_version
        orm.deleted_at = document.deleted_at
        orm.document_type = document.document_type
        updated = await super().update(orm, skip_existence_check=True)
        return _document_to_result(updated)

    async def count_by_subjects_and_document_type(
        self,
        tenant_id: str,
        subject_ids: list[str],
        document_type: str,
    ) -> int:
        """Count non-deleted documents for the given subjects and document_type (e.g. category_name)."""
        if not subject_ids:
            return 0
        result = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == tenant_id,
                Document.subject_id.in_(subject_ids),
                Document.document_type == document_type,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

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
        """Return this document plus all descendants in the version chain (recursive by parent_document_id), ordered by version."""
        anchor = select(Document.id).where(
            and_(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        version_chain = anchor.cte(name="version_chain", recursive=True)
        chain_alias = version_chain.alias()
        recursive_part = select(Document.id).where(
            and_(
                Document.parent_document_id == chain_alias.c.id,
                Document.tenant_id == tenant_id,
            )
        )
        version_chain = version_chain.union_all(recursive_part)
        stmt = (
            select(Document)
            .where(Document.id.in_(select(version_chain.c.id)))
            .order_by(Document.version.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        if not any(d.id == document_id for d in rows):
            return []
        return [_document_to_result(d) for d in rows]

    async def list_by_tenant(
        self,
        tenant_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        document_type: str | None = None,
        include_deleted: bool = False,
        created_before: datetime | None = None,
    ) -> list[DocumentResult]:
        """List documents for tenant (for retention job and admin)."""
        q = select(Document).where(Document.tenant_id == tenant_id)
        if not include_deleted:
            q = q.where(Document.deleted_at.is_(None))
        if document_type is not None:
            q = q.where(Document.document_type == document_type)
        if created_before is not None:
            q = q.where(Document.created_at < created_before)
        q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return [_document_to_result(d) for d in result.scalars().all()]

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
        updated = await super().update(orm, skip_existence_check=True)
        await self.emit_custom_audit(updated, AuditAction.DELETED)
        return _document_to_result(updated)
