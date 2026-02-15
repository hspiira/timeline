"""Search API schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class SearchResultItemResponse(BaseModel):
    """Single search hit (subject, event, or document)."""

    resource_type: Literal["subject", "event", "document"] = Field(
        ..., description="subject | event | document"
    )
    id: str
    tenant_id: str
    snippet: str | None = None
    subject_id: str | None = None
    display_title: str


class SearchResponse(BaseModel):
    """Full-text search response (list of hits)."""

    results: list[SearchResultItemResponse]
