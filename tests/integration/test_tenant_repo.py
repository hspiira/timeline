"""Tenant repository integration tests. Require Postgres; session is rolled back after each test."""

import pytest

from app.domain.enums import TenantStatus
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository


@pytest.mark.requires_db
async def test_create_tenant_and_get_by_code(db_session) -> None:
    """Create a tenant then get it by code."""
    repo = TenantRepository(db_session, cache_service=None, audit_service=None)
    created = await repo.create_tenant(
        code="repo-test-code",
        name="Repo Test Tenant",
        status=TenantStatus.ACTIVE,
    )
    assert created.id
    assert created.code == "repo-test-code"
    assert created.name == "Repo Test Tenant"
    assert created.status == TenantStatus.ACTIVE

    found = await repo.get_by_code("repo-test-code")
    assert found is not None
    assert found.id == created.id
    assert found.code == created.code
    assert found.name == created.name


@pytest.mark.requires_db
async def test_get_by_id(db_session) -> None:
    """Create tenant then get by id."""
    repo = TenantRepository(db_session, cache_service=None, audit_service=None)
    created = await repo.create_tenant(
        code="repo-test-by-id",
        name="By Id Tenant",
        status=TenantStatus.ACTIVE,
    )
    found = await repo.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id
    assert found.code == "repo-test-by-id"


@pytest.mark.requires_db
async def test_get_by_code_not_found_returns_none(db_session) -> None:
    """get_by_code returns None for unknown code."""
    repo = TenantRepository(db_session, cache_service=None, audit_service=None)
    found = await repo.get_by_code("nonexistent-code-xyz")
    assert found is None


@pytest.mark.requires_db
async def test_get_by_id_not_found_returns_none(db_session) -> None:
    """get_by_id returns None for unknown id."""
    repo = TenantRepository(db_session, cache_service=None, audit_service=None)
    found = await repo.get_by_id("nonexistent-id-xyz")
    assert found is None
