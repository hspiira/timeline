"""Subject data export and erasure use cases (GDPR-style)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from app.application.dtos.event import EventResult
from app.application.dtos.subject_export import SubjectExportResult
from app.application.interfaces.repositories import (
    IDocumentRepository,
    IEventRepository,
    ISubjectRepository,
)
from app.domain.exceptions import ResourceNotFoundException
from app.shared.utils.datetime import utc_now


class ErasureStrategy(str, Enum):
    """Strategy for subject data erasure."""

    ANONYMIZE = "anonymize"
    DELETE = "delete"


def _subject_to_export_dict(tenant_id: str, subject: Any) -> dict[str, Any]:
    """Build JSON-serializable subject dict for export."""
    st = getattr(subject, "subject_type", None)
    type_val = st.value if hasattr(st, "value") else str(st)
    return {
        "id": subject.id,
        "tenant_id": subject.tenant_id,
        "subject_type": type_val,
        "external_ref": subject.external_ref,
        "display_name": getattr(subject, "display_name", None) or "",
        "attributes": getattr(subject, "attributes", None) or {},
    }


def _event_to_export_dict(event: EventResult) -> dict[str, Any]:
    """Build JSON-serializable event dict for export."""
    return {
        "id": event.id,
        "subject_id": event.subject_id,
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "event_time": event.event_time.isoformat() if event.event_time else None,
        "payload": event.payload,
    }


def _document_to_export_dict(doc: Any) -> dict[str, Any]:
    """Build document metadata dict for export (no binary; download via document API)."""
    return {
        "id": doc.id,
        "subject_id": doc.subject_id,
        "event_id": doc.event_id,
        "document_type": doc.document_type,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "version": doc.version,
    }


class SubjectExportService:
    """Export all data for a subject (events, document refs) as structured JSON."""

    def __init__(
        self,
        subject_repo: ISubjectRepository,
        event_repo: IEventRepository,
        document_repo: IDocumentRepository,
    ) -> None:
        self._subject_repo = subject_repo
        self._event_repo = event_repo
        self._document_repo = document_repo

    async def export_subject_data(
        self, tenant_id: str, subject_id: str
    ) -> SubjectExportResult:
        """Export subject, its events, and document metadata (no file binary).

        Document files can be downloaded via the document API using the returned ids.
        """
        subject = await self._subject_repo.get_by_id_and_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)

        events = await self._event_repo.get_by_subject(
            subject_id=subject_id,
            tenant_id=tenant_id,
            skip=0,
            limit=10_000,
        )
        docs = await self._document_repo.get_by_subject(
            subject_id=subject_id,
            tenant_id=tenant_id,
            include_deleted=False,
        )

        return SubjectExportResult(
            subject=_subject_to_export_dict(tenant_id, subject),
            events=[_event_to_export_dict(e) for e in events],
            documents=[_document_to_export_dict(d) for d in docs],
            exported_at=utc_now(),
        )


class SubjectErasureService:
    """Erasure (anonymize or delete) of subject-related data for GDPR."""

    def __init__(
        self,
        subject_repo: ISubjectRepository,
        document_repo: IDocumentRepository,
    ) -> None:
        self._subject_repo = subject_repo
        self._document_repo = document_repo

    async def erase_subject_data(
        self,
        tenant_id: str,
        subject_id: str,
        strategy: ErasureStrategy,
    ) -> None:
        """Anonymize or delete subject and linked document metadata.

        - anonymize: Set subject external_ref, display_name, attributes to redacted
          placeholders; soft-delete documents for the subject (metadata retained but
          marked deleted). Events are immutable and are not modified.
        - delete: Hard-delete subject, soft-delete all documents for the subject.
          Events remain for chain integrity but are no longer reachable via subject.
        """
        subject = await self._subject_repo.get_by_id_and_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)

        if strategy == ErasureStrategy.ANONYMIZE:
            await self._subject_repo.update_subject(
                tenant_id=tenant_id,
                subject_id=subject_id,
                external_ref="[REDACTED]",
                display_name="[REDACTED]",
                attributes={},
            )
            docs = await self._document_repo.get_by_subject(
                subject_id=subject_id,
                tenant_id=tenant_id,
                include_deleted=True,
            )
            for doc in docs:
                if doc.deleted_at is None:
                    await self._document_repo.soft_delete(doc.id, tenant_id)
        else:
            await self._subject_repo.delete_subject(
                tenant_id=tenant_id,
                subject_id=subject_id,
            )
