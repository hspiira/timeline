"""Row-level security keeps one organisation's records out of another's reach.

``rls_check`` verifies the policies are configured; these verify they bite.

Two sessions per test, because one cannot do both jobs. ``db_session`` is the
migrating role and creates the fixtures: the policy on ``tenant`` checks the new row
against ``app.current_tenant_id``, so a restricted role cannot insert a tenant at all.
``rls_session`` is a deliberately powerless role and makes the assertions, because
row-level security does not apply to a superuser, to BYPASSRLS, or to the table owner.
That is the production split, and it is why these tests used to skip in CI: the only
session available was the one the policies ignore.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.application.dtos.event import EventCreate
from app.application.services.hash_service import HashService
from app.application.use_cases.events.create_event import EventService
from app.domain.enums import TenantStatus
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.shared.utils.datetime import utc_now

pytestmark = pytest.mark.requires_db


async def _point_at(session, tenant_id: str) -> None:
    """Scope the session to one organisation, as the application does per request."""
    # set_config takes a bind parameter; SET LOCAL would need the id interpolated.
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": tenant_id}
    )


async def _organisation_with_one_event(session) -> tuple[str, str, str]:
    """Create an organisation with one subject and one event; returns their ids.

    Rows are left behind because events cannot be deleted; "iso-" marks them.
    """
    tenant_repo = TenantRepository(session, cache_service=None, audit_service=None)
    tenant = await tenant_repo.create_tenant(
        code=f"iso-{uuid.uuid4().hex[:6]}",
        name="Isolation Test",
        status=TenantStatus.ACTIVE,
    )
    subject_repo = SubjectRepository(session, tenant_id=tenant.id, audit_service=None)
    subject = await subject_repo.create_subject(
        tenant_id=tenant.id,
        subject_type="client",
        external_ref=f"ISO-{uuid.uuid4().hex[:8]}",
    )
    await session.commit()

    service = EventService(
        event_repo=EventRepository(session),
        hash_service=HashService(),
        subject_repo=SubjectRepository(
            session, tenant_id=tenant.id, audit_service=None
        ),
        db=session,
        schema_validator=None,
        transition_validator=None,
        post_create_hooks=[],
    )
    event = await service.create_event(
        tenant_id=tenant.id,
        data=EventCreate(
            subject_id=subject.id,
            event_type="client",
            schema_version=1,
            event_time=utc_now(),
            payload={"name": "Private"},
        ),
        trigger_workflows=False,
    )
    return tenant.id, subject.id, event.id


async def test_one_organisation_cannot_read_another_s_rows(db_session, rls_session) -> None:
    """Pointed at organisation A, a raw query returns none of organisation B's rows.

    Raw SQL, not a repository: a repository filters by tenant id itself and would
    pass even with the policies dropped.
    """
    tenant_a, subject_a, event_a = await _organisation_with_one_event(db_session)
    tenant_b, subject_b, event_b = await _organisation_with_one_event(db_session)
    assert tenant_a != tenant_b

    await _point_at(rls_session, tenant_a)

    visible_events = (
        await rls_session.execute(text("SELECT id FROM event"))
    ).scalars().all()
    assert event_a in visible_events
    assert event_b not in visible_events, "another organisation's event was readable"

    visible_subjects = (
        await rls_session.execute(text("SELECT id FROM subject"))
    ).scalars().all()
    assert subject_a in visible_subjects
    assert subject_b not in visible_subjects, "another organisation's subject was readable"

    # Naming the row directly must not defeat the policy either.
    targeted = (
        await rls_session.execute(
            text("SELECT id FROM event WHERE id = :i"), {"i": event_b}
        )
    ).scalars().all()
    assert targeted == [], "asking for the row by id still must not return it"


async def test_a_repository_cannot_reach_across_organisations(db_session, rls_session) -> None:
    """An id that leaks and is replayed against another organisation returns nothing.

    Two barriers, checked separately because they fail independently.
    TenantScopedRepository puts ``tenant_id = <its own>`` in the SQL, so the first
    assertion holds even with the policies dropped. The second scopes the repository
    to organisation B while the session is pointed at A, which is what a leaked or
    forged tenant id would do: the repository's own filter now agrees with the
    attacker, and row-level security is the only thing left saying no.
    """
    tenant_a, _, _ = await _organisation_with_one_event(db_session)
    tenant_b, subject_b, _ = await _organisation_with_one_event(db_session)

    await _point_at(rls_session, tenant_a)

    scoped_to_a = SubjectRepository(rls_session, tenant_id=tenant_a, audit_service=None)
    assert await scoped_to_a.get_by_id(subject_b) is None, (
        "the repository's own tenant filter let another organisation's row through"
    )

    scoped_to_b = SubjectRepository(rls_session, tenant_id=tenant_b, audit_service=None)
    assert await scoped_to_b.get_by_id(subject_b) is None, (
        "a repository scoped to another organisation reached its rows; the policies "
        "are the last barrier here and did not hold"
    )


async def test_writes_cannot_be_attributed_to_another_organisation(db_session, rls_session) -> None:
    """An insert naming a different organisation is refused, so the policies guard
    writes and not only reads.
    """
    tenant_a, _, _ = await _organisation_with_one_event(db_session)
    tenant_b, _, _ = await _organisation_with_one_event(db_session)

    await _point_at(rls_session, tenant_a)

    statement = text(
        "INSERT INTO subject (id, tenant_id, subject_type, external_ref) "
        "VALUES (:i, :t, 'client', :r)"
    )
    parameters = {
        "i": f"planted{uuid.uuid4().hex[:12]}",
        "t": tenant_b,
        "r": f"PLANTED-{uuid.uuid4().hex[:8]}",
    }

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        await rls_session.execute(statement, parameters)


async def test_every_tenant_scoped_table_has_a_policy(db_session) -> None:
    """A tenant-scoped table with no policy is an isolation hole nothing else catches.

    The tests above prove the policies bite on subject and event. This one is the
    inventory check: add a table with a tenant_id and forget the RLS migration, and
    every other test still passes while that table is readable across organisations.
    """
    unprotected = (
        await db_session.execute(
            text(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND EXISTS (
                      SELECT 1 FROM information_schema.columns col
                      WHERE col.table_schema = 'public'
                        AND col.table_name = c.relname
                        AND col.column_name = 'tenant_id'
                  )
                  AND (
                      NOT c.relrowsecurity
                      OR NOT EXISTS (
                          SELECT 1 FROM pg_policies p
                          WHERE p.schemaname = 'public' AND p.tablename = c.relname
                      )
                  )
                ORDER BY c.relname
                """
            )
        )
    ).scalars().all()

    assert unprotected == [], (
        "these tables carry a tenant_id but no row-level security policy, so their "
        f"rows are readable across organisations: {', '.join(unprotected)}"
    )
