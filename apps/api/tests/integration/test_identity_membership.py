"""One person, one password, separate access per organisation.

Covers the behaviour that motivated splitting ``identity`` from ``app_user``
(migration e3f4g5h6i7j8): a human has a single credential, but their access to each
organisation is independent. Previously each organisation held its own password
hash for the same person, so there was no single source of truth.

Every tenant-scoped read or write sets the session's tenant context first, because
row-level security demands it and ``SET LOCAL`` lasts only for the transaction. A
real request does this once in middleware; a test touching two organisations in one
transaction has to switch between them.
"""

import pytest
from sqlalchemy import text

from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.repositories.user_repo import UserRepository

pytestmark = pytest.mark.requires_db

EMAIL = "shared.person@example.test"
PASSWORD = "first-password-123"


async def _use(session, tenant_id: str) -> None:
    """Point the session's row-level security context at one organisation."""
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))


async def _make_tenant(session, suffix: str) -> str:
    """Insert a tenant, which requires the context to already be its own id."""
    tenant_id = f"itest_{suffix}"
    await _use(session, tenant_id)
    session.add(
        Tenant(
            id=tenant_id,
            code=f"itest-{suffix}",
            name=f"Test Org {suffix.upper()}",
            status="Active",
        )
    )
    await session.flush()
    return tenant_id


async def _add_person(repo, session, tenant_id: str, password: str):
    """Add the shared person to one organisation."""
    await _use(session, tenant_id)
    membership = await repo.create_user(tenant_id, "person", EMAIL, password)
    await session.flush()
    return membership


async def _sign_in(repo, session, tenant_id: str, password: str):
    """Attempt sign-in to one organisation."""
    await _use(session, tenant_id)
    return await repo.authenticate(EMAIL, tenant_id, password)


async def test_one_identity_shared_across_organisations(db_session) -> None:
    """The same email in two organisations is one person with one password."""
    first = await _make_tenant(db_session, "aaa")
    second = await _make_tenant(db_session, "bbb")
    repo = UserRepository(db_session, enable_audit=False)

    # Deliberately mixed case, and a different password the second time.
    await _add_person(repo, db_session, first, PASSWORD)
    await _use(db_session, second)
    await repo.create_user(second, "person", EMAIL.upper(), "some-other-password")
    await db_session.flush()

    count = await db_session.execute(
        text("SELECT count(*) FROM identity WHERE email = :e"), {"e": EMAIL}
    )
    assert count.scalar() == 1, "one human should have exactly one credential"

    # Stored lower-cased, so capitalisation cannot split one person into two.
    stored = await db_session.execute(
        text("SELECT email FROM identity WHERE email = :e"), {"e": EMAIL}
    )
    assert stored.scalar() == EMAIL

    # The first password works in both organisations, and the second was ignored.
    assert await _sign_in(repo, db_session, first, PASSWORD) is not None
    assert await _sign_in(repo, db_session, second, PASSWORD) is not None
    assert await _sign_in(repo, db_session, second, "some-other-password") is None


async def test_deactivating_in_one_organisation_does_not_affect_the_other(
    db_session,
) -> None:
    """Removing someone from one organisation must not lock them out of another."""
    first = await _make_tenant(db_session, "ccc")
    second = await _make_tenant(db_session, "ddd")
    repo = UserRepository(db_session, enable_audit=False)

    await _add_person(repo, db_session, first, PASSWORD)
    membership_two = await _add_person(repo, db_session, second, PASSWORD)

    await _use(db_session, second)
    await repo.deactivate(membership_two.id, second)
    await db_session.flush()

    assert await _sign_in(repo, db_session, first, PASSWORD) is not None, (
        "deactivation in one organisation must not affect another"
    )
    assert await _sign_in(repo, db_session, second, PASSWORD) is None

    # The organisation they were removed from stops being offered at sign-in. This
    # goes through signin_organisations(), which is not tenant-scoped.
    offered = {tid for tid, _ in await repo.get_organisations_for_email(EMAIL)}
    assert first in offered
    assert second not in offered


async def test_password_change_applies_everywhere(db_session) -> None:
    """Changing the password is one change, because it lives on the identity."""
    first = await _make_tenant(db_session, "eee")
    second = await _make_tenant(db_session, "fff")
    repo = UserRepository(db_session, enable_audit=False)

    membership_one = await _add_person(repo, db_session, first, PASSWORD)
    await _add_person(repo, db_session, second, PASSWORD)

    await _use(db_session, first)
    await repo.update_password(membership_one.id, "second-password-456")
    await db_session.flush()

    for tenant_id in (first, second):
        assert await _sign_in(repo, db_session, tenant_id, PASSWORD) is None
        assert (
            await _sign_in(repo, db_session, tenant_id, "second-password-456")
            is not None
        )
