"""Document API schemas."""

from pydantic import BaseModel, Field


class DocumentUpdate(BaseModel):
    """Request body for PATCH/PUT document (partial)."""

    document_type: str | None = Field(default=None, max_length=128)
