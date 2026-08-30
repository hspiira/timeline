"""Full-text search use case. Delegates to ISearchRepository."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.search import SearchResultItem

if TYPE_CHECKING:
    from app.application.interfaces.repositories import ISearchRepository


class SearchService:
    """Full-text search across subjects, events, and documents (tenant-scoped)."""

    def __init__(self, search_repo: "ISearchRepository") -> None:
        self.search_repo = search_repo

    async def search(
        self,
        tenant_id: str,
        q: str,
        scope: str = "all",
        limit: int = 50,
    ) -> list[SearchResultItem]:
        """Search within tenant. scope: all | subjects | events | documents."""
        allowed = ("all", "subjects", "events", "documents")
        if scope not in allowed:
            scope = "all"
        return await self.search_repo.full_text_search(
            tenant_id=tenant_id, q=q, scope=scope, limit=limit
        )
