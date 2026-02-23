"""Full-text search repository. Uses PostgreSQL tsvector on subject and event."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.search import SearchResultItem


class SearchRepository:
    """Full-text search across subjects, events, and documents (metadata)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def full_text_search(
        self,
        tenant_id: str,
        q: str,
        scope: str = "all",
        limit: int = 50,
    ) -> list[SearchResultItem]:
        """Search within tenant. scope: all | subjects | events | documents."""
        if not q or not q.strip():
            return []
        limit = min(max(1, limit), 100)
        query = q.strip()
        results: list[SearchResultItem] = []

        per_scope = (limit + 2) // 3 if scope == "all" else limit
        if scope in ("all", "subjects"):
            results.extend(await self._search_subjects(tenant_id, query, per_scope))
        if scope in ("all", "events"):
            results.extend(await self._search_events(tenant_id, query, per_scope))
        if scope in ("all", "documents"):
            results.extend(await self._search_documents(tenant_id, query, per_scope))

        if scope == "all":
            results = results[:limit]
        return results

    async def _search_subjects(
        self, tenant_id: str, query: str, limit: int
    ) -> list[SearchResultItem]:
        """Full-text search on subject (search_vector)."""
        stmt = text("""
            SELECT s.id, s.tenant_id,
                   ts_headline('english', coalesce(s.display_name, '') || ' ' || coalesce(s.external_ref, '') || ' ' || coalesce(s.attributes::text, ''),
                     plainto_tsquery('english', :q), 'MaxFragments=1, MaxWords=30, MinWords=15') AS snippet,
                   coalesce(s.display_name, s.external_ref, s.id) AS display_title
            FROM subject s
            WHERE s.tenant_id = :tenant_id
              AND s.search_vector @@ plainto_tsquery('english', :q)
            ORDER BY ts_rank(s.search_vector, plainto_tsquery('english', :q)) DESC
            LIMIT :limit
        """)
        r = await self.db.execute(
            stmt, {"tenant_id": tenant_id, "q": query, "limit": limit}
        )
        rows = r.mappings().all()
        return [
            SearchResultItem(
                resource_type="subject",
                id=row["id"],
                tenant_id=row["tenant_id"],
                snippet=row["snippet"] if row["snippet"] else None,
                subject_id=None,
                display_title=row["display_title"] or row["id"],
            )
            for row in rows
        ]

    async def _search_events(
        self, tenant_id: str, query: str, limit: int
    ) -> list[SearchResultItem]:
        """Full-text search on event (search_vector)."""
        stmt = text("""
            SELECT e.id, e.tenant_id, e.subject_id,
                   ts_headline('english', coalesce(e.event_type, '') || ' ' || coalesce(e.payload::text, ''),
                     plainto_tsquery('english', :q), 'MaxFragments=1, MaxWords=30, MinWords=15') AS snippet,
                   e.event_type AS display_title
            FROM event e
            WHERE e.tenant_id = :tenant_id
              AND e.search_vector @@ plainto_tsquery('english', :q)
            ORDER BY ts_rank(e.search_vector, plainto_tsquery('english', :q)) DESC
            LIMIT :limit
        """)
        r = await self.db.execute(
            stmt, {"tenant_id": tenant_id, "q": query, "limit": limit}
        )
        rows = r.mappings().all()
        return [
            SearchResultItem(
                resource_type="event",
                id=row["id"],
                tenant_id=row["tenant_id"],
                snippet=row["snippet"] if row["snippet"] else None,
                subject_id=row["subject_id"],
                display_title=row["display_title"] or row["id"],
            )
            for row in rows
        ]

    async def _search_documents(
        self, tenant_id: str, query: str, limit: int
    ) -> list[SearchResultItem]:
        """Search documents by filename, original_filename, document_type (ILIKE)."""
        # Escape ILIKE wildcards % and _ so query is literal
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = text("""
            SELECT d.id, d.tenant_id, d.subject_id,
                   coalesce(d.original_filename, d.filename) AS display_title
            FROM document d
            WHERE d.tenant_id = :tenant_id
              AND d.deleted_at IS NULL
              AND (d.filename ILIKE :pattern ESCAPE '\\' OR d.original_filename ILIKE :pattern ESCAPE '\\' OR d.document_type ILIKE :pattern ESCAPE '\\')
            ORDER BY d.created_at DESC
            LIMIT :limit
        """)
        r = await self.db.execute(
            stmt, {"tenant_id": tenant_id, "pattern": pattern, "limit": limit}
        )
        rows = r.mappings().all()
        return [
            SearchResultItem(
                resource_type="document",
                id=row["id"],
                tenant_id=row["tenant_id"],
                snippet=None,
                subject_id=row["subject_id"],
                display_title=row["display_title"] or row["id"],
            )
            for row in rows
        ]
