"""Document API schemas."""

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    """Response for POST upload (document created)."""

    id: str
    filename: str


class DocumentDownloadUrlResponse(BaseModel):
    """Response for GET /{document_id}/download-url."""

    url: str
    expires_in_hours: int


class DocumentListItem(BaseModel):
    """Document list item (by event or list)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime_type: str | None = None
    file_size: int | None = None
    version: int | None = None


class DocumentVersionItem(BaseModel):
    """Document version in version chain."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    subject_id: str
    filename: str
    mime_type: str | None = None
    file_size: int | None = None
    version: int | None = None


class DocumentUpdate(BaseModel):
    """Request body for PATCH/PUT document (partial)."""

    document_type: str | None = Field(default=None, max_length=128)
