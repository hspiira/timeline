"""Run document retention: soft-delete documents past category default_retention_days."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.application.dtos.retention import RetentionRunResult

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IDocumentCategoryRepository,
        IDocumentRepository,
    )


# Batch size for listing documents per category (avoid loading too many at once)
RETENTION_BATCH_SIZE = 500


class RunDocumentRetentionUseCase:
    """Soft-deletes documents that are past their category's default_retention_days.

    For each document category in the tenant that has default_retention_days set,
    lists documents with document_type equal to the category's category_name and
    created_at before (now - retention_days), then soft-deletes them.
    """

    def __init__(
        self,
        document_repo: "IDocumentRepository",
        document_category_repo: "IDocumentCategoryRepository",
    ) -> None:
        self._document_repo = document_repo
        self._document_category_repo = document_category_repo

    async def run(self, tenant_id: str) -> RetentionRunResult:
        """Run retention for the given tenant.

        Fetches all document categories for the tenant that have
        default_retention_days set. For each such category, finds documents
        with document_type == category_name and created_at before the
        retention cutoff, and soft-deletes them.

        Returns:
            Summary with tenant_id and per-category soft-delete counts.
        """
        categories = await self._document_category_repo.get_by_tenant(
            tenant_id=tenant_id,
            skip=0,
            limit=1000,
        )
        soft_deleted_by_category: dict[str, int] = {}
        now = datetime.now(UTC)
        for cat in categories:
            if cat.default_retention_days is None or cat.default_retention_days < 1:
                continue
            cutoff = now - timedelta(days=cat.default_retention_days)
            count = 0
            skip = 0
            while True:
                docs = await self._document_repo.list_by_tenant(
                    tenant_id,
                    skip=skip,
                    limit=RETENTION_BATCH_SIZE,
                    document_type=cat.category_name,
                    include_deleted=False,
                    created_before=cutoff,
                )
                if not docs:
                    break
                for doc in docs:
                    await self._document_repo.soft_delete(doc.id, tenant_id)
                    count += 1
                skip += len(docs)
                if len(docs) < RETENTION_BATCH_SIZE:
                    break
            if count > 0:
                soft_deleted_by_category[cat.category_name] = count
        return RetentionRunResult(
            tenant_id=tenant_id,
            soft_deleted_by_category=soft_deleted_by_category,
        )
