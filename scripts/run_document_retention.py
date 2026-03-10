"""Run document retention: soft-delete documents older than default_document_retention_days.

Usage:
    uv run python -m scripts.run_document_retention [tenant_id]
If tenant_id is omitted, processes all active tenants.
Requires Postgres and DEFAULT_DOCUMENT_RETENTION_DAYS set in config.
"""

import asyncio
import sys
from datetime import timedelta

from app.core.config import get_settings
import app.infrastructure.persistence.database as database
from app.infrastructure.persistence.repositories import DocumentRepository, TenantRepository
from app.shared.utils.datetime import utc_now


async def main() -> None:
    """For each tenant, soft-delete documents past retention."""
    settings = get_settings()
    database._ensure_engine()
    if database.AsyncSessionLocal is None:
        print("AsyncSessionLocal not configured", file=sys.stderr)
        sys.exit(1)
    retention_days = get_settings().default_document_retention_days
    if retention_days is None or retention_days < 1:
        print(
            "Set DEFAULT_DOCUMENT_RETENTION_DAYS (>= 1) to enable retention",
            file=sys.stderr,
        )
        sys.exit(1)

    cutoff = utc_now() - timedelta(days=retention_days)
    tenant_filter = sys.argv[1] if len(sys.argv) > 1 else None

    # Fetch active tenants in a short-lived transaction
    async with database.AsyncSessionLocal() as session:
        async with session.begin():
            tenant_repo = TenantRepository(session, cache_service=None, audit_service=None)
            tenants = await tenant_repo.get_active_tenants(skip=0, limit=10_000)
    if tenant_filter:
        tenants = [t for t in tenants if t.id == tenant_filter or t.code == tenant_filter]
        if not tenants:
            print(f"Tenant not found: {tenant_filter}", file=sys.stderr)
            sys.exit(1)

    total_deleted = 0
    batch_size = 500

    for tenant in tenants:
        tenant_deleted = 0
        async with database.AsyncSessionLocal() as session:
            async with session.begin():
                doc_repo = DocumentRepository(session, audit_service=None)
                while True:
                    docs = await doc_repo.list_by_tenant(
                        tenant.id,
                        skip=0,
                        limit=batch_size,
                        include_deleted=False,
                        created_before=cutoff,
                    )
                    if not docs:
                        break
                    for doc in docs:
                        await doc_repo.soft_delete(doc.id, tenant.id)
                        tenant_deleted += 1
                        total_deleted += 1
        if tenant_deleted > 0:
            print(f"Tenant {tenant.code}: soft-deleted {tenant_deleted} document(s)")

    print(f"Done. Total soft-deleted: {total_deleted}")


if __name__ == "__main__":
    asyncio.run(main())
