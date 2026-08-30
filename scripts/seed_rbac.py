"""Seed RBAC (permissions, roles, role-permissions, audit schema) for an existing tenant.

Usage:
    uv run python -m scripts.seed_rbac <tenant_id_or_code>
Resolves tenant by id or code. Requires Postgres. All imports use app.*.
"""

import asyncio
import sys

from app.infrastructure.persistence.repositories import TenantRepository
from scripts._session import fail, open_session, use_tenant
from app.infrastructure.services.tenant_initialization_service import (
    TenantInitializationService,
)


async def main() -> None:
    """Seed RBAC for the given tenant."""
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python -m scripts.seed_rbac <tenant_id_or_code>",
            file=sys.stderr,
        )
        sys.exit(1)
    tenant_arg = sys.argv[1]

    async with open_session() as session:
        async with session.begin():
            tenant_repo = TenantRepository(
                session, cache_service=None, audit_service=None
            )
            tenant = await tenant_repo.get_by_id(
                tenant_arg
            ) or await tenant_repo.get_by_code(tenant_arg)
            if not tenant:
                fail(f"Tenant not found: {tenant_arg}")
            await use_tenant(session, tenant.id)
            init_svc = TenantInitializationService(session)
            await init_svc.initialize_tenant_infrastructure(tenant.id)
            print(f"Seeded RBAC for tenant {tenant.id} ({tenant.code})")


if __name__ == "__main__":
    asyncio.run(main())
