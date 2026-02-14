"""DTOs for full-text search results (no dependency on ORM)."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SearchResultItem:
    """Single search hit: subject, event, or document (read-model)."""

    resource_type: Literal["subject", "event", "document"]
    id: str
    tenant_id: str
    snippet: str | None
    subject_id: str | None  # For event and document; None for subject
    # Extra context for display
    display_title: str  # e.g. display_name for subject, event_type for event, filename for document
