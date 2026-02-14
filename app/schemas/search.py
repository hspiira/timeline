"""Search API schemas."""

from pydantic import BaseModel, Field


class SearchResultItemResponse(BaseModel):
    """Single search hit (subject, event, or document)."""

    resource_type: str = Field(..., description="subject | event | document")
    id: str
    tenant_id: str
    snippet: str | None = None
    subject_id: str | None = None
    display_title: str


class SearchResponse(BaseModel):
    """Full-text search response (list of hits)."""

    results: list[SearchResultItemResponse]
