"""DTOs for document use cases (no dependency on ORM)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DocumentResult:
    """Document read-model (result of get_by_id, get_by_subject, get_by_checksum, create, update)."""

    id: str
    tenant_id: str
    subject_id: str
    event_id: str | None
    document_type: str
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    checksum: str
    storage_ref: str
    version: int
    parent_document_id: str | None
    is_latest_version: bool
    created_by: str | None
    deleted_at: datetime | None


@dataclass
class DocumentMetadata:
    """Document metadata for get_document_metadata (subset of DocumentResult)."""

    id: str
    tenant_id: str
    subject_id: str
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    version: int
    storage_ref: str


@dataclass
class DocumentListItem:
    """Document list item for list_documents (minimal fields)."""

    id: str
    filename: str
    mime_type: str
    file_size: int
    version: int
