"""Document repository with audit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.document import Document
from app.infrastructure.persistence.repositories.auditable_repo import AuditableRepository
from app.shared.enums import AuditAction
from app.shared.utils import utc_now

if TYPE_CHECKING:
    from app.application.services.system_audit_service import SystemAuditService


class DocumentRepository(AuditableRepository[Document]):
    """Document repository."""

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

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        include_deleted: bool = False,
    ) -> list[Document]:
        q = select(Document).where(
            and_(Document.subject_id == subject_id, Document.tenant_id == tenant_id)
        )
        if not include_deleted:
            q = q.where(Document.deleted_at.is_(None))
        q = q.order_by(Document.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_event(self, event_id: str, tenant_id: str) -> list[Document]:
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
        return list(result.scalars().all())

    async def get_by_checksum(self, tenant_id: str, checksum: str) -> Document | None:
        result = await self.db.execute(
            select(Document).where(
                and_(
                    Document.tenant_id == tenant_id,
                    Document.checksum == checksum,
                    Document.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, document_id: str) -> Document | None:
        doc = await self.get_by_id(document_id)
        if not doc:
            return None
        doc.deleted_at = utc_now()
        updated = await self.update(doc)
        await self.emit_custom_audit(updated, AuditAction.DELETED)
        return updated
