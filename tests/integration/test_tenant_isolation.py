"""Row-level security keeps one organisation's records out of another's reach.

``rls_check`` verifies that the policies and roles are configured. This verifies
that they actually bite: with the session pointed at one organisation, the rows of
another are not merely filtered out of the application's queries but are invisible
to the connection itself.

Every test here skips when the connected role can bypass row-level security, since
a role with BYPASSRLS sees everything by design and would report a pass that means
nothing. Run as the restricted application role to exercise them.
"""

import uuid

import pytest
from sqlalchemy import text

from app.application.dtos.event import EventCreate
from app.application.services.hash_service import HashService
from app.application.use_cases.events.create_event import EventService
from app.domain.enums import TenantStatus
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.shared.utils.datetime import utc_now

pytestmark = pytest.mark.requires_db


async def _skip_if_role_bypasses_rls(session) -> None:
    """Skip the calling test when the connected role is exempt from RLS."""
    bypasses = await session.execute(
        text("SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user")
    )
    if bool(bypasses.scalar()):
        pytest.skip(
            "Connected role bypasses row-level security, so isolation cannot be "
            "observed. Run as the restricted application role instead."
        )


async def _organisation_with_one_event(session) -> tuple[str, str, str]:
    """Create an organisation holding a subject and a single event.

    Returns the organisation, subject and event ids. Rows are left behind because
    events cannot be deleted; the "iso-" prefix marks them for later pruning.
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


async def test_one_organisation_cannot_read_another_s_rows(db_session) -> None:
    """Pointed at organisation A, a raw query returns none of organisation B's rows.

    The read is deliberately made in SQL rather than through a repository. A
    repository filters by tenant id itself, so it would pass this test even if the
    policies were dropped entirely; only the unfiltered query shows whether the
    database is doing the work.
    """
    await _skip_if_role_bypasses_rls(db_session)

    tenant_a, subject_a, event_a = await _organisation_with_one_event(db_session)
    tenant_b, subject_b, event_b = await _organisation_with_one_event(db_session)
    assert tenant_a != tenant_b

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_a}'"))

    visible_events = (
        await db_session.execute(text("SELECT id FROM event"))
    ).scalars().all()
    assert event_a in visible_events
    assert event_b not in visible_events, "another organisation's event was readable"

    visible_subjects = (
        await db_session.execute(text("SELECT id FROM subject"))
    ).scalars().all()
    assert subject_a in visible_subjects
    assert subject_b not in visible_subjects, "another organisation's subject was readable"

    # Naming the row directly must not defeat the policy either.
    targeted = (
        await db_session.execute(
            text("SELECT id FROM event WHERE id = :i"), {"i": event_b}
        )
    ).scalars().all()
    assert targeted == [], "asking for the row by id still must not return it"

    await db_session.rollback()


async def test_a_repository_cannot_reach_across_organisations(db_session) -> None:
    """Asking for another organisation's subject by id returns nothing.

    Covers the case where an id leaks and is replayed against a session belonging to
    a different organisation.
    """
    await _skip_if_role_bypasses_rls(db_session)

    tenant_a, _, _ = await _organisation_with_one_event(db_session)
    _, subject_b, _ = await _organisation_with_one_event(db_session)

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_a}'"))

    repo = SubjectRepository(db_session, tenant_id=tenant_a, audit_service=None)
    assert await repo.get_by_id(subject_b) is None

    await db_session.rollback()


async def test_writes_cannot_be_attributed_to_another_organisation(db_session) -> None:
    """An insert naming a different organisation is refused rather than accepted.

    Without this the policies would guard reads only, and a compromised session
    could still plant records in someone else's timeline.
    """
    await _skip_if_role_bypasses_rls(db_session)

    tenant_a, _, _ = await _organisation_with_one_event(db_session)
    tenant_b, _, _ = await _organisation_with_one_event(db_session)

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_a}'"))

    with pytest.raises(Exception):
        await db_session.execute(
            text(
                "INSERT INTO subject (id, tenant_id, subject_type, external_ref) "
                "VALUES (:i, :t, 'client', :r)"
            ),
            {
                "i": f"planted{uuid.uuid4().hex[:12]}",
                "t": tenant_b,
                "r": f"PLANTED-{uuid.uuid4().hex[:8]}",
            },
        )
    await db_session.rollback()
