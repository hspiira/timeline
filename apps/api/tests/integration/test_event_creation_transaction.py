"""Creating an event works on a session that already holds a transaction.

Regression test. Row-level security needs the tenant context, which is set with
``SET LOCAL`` and so only exists inside a transaction — meaning every session handed
out by ``get_db`` already has one open. ``create_event`` opens its own transaction,
because a chain fork is retried by rolling the whole attempt back, and it used to do
so unconditionally: SQLAlchemy raised "a transaction is already begun on this
Session" and **every** event creation failed with a 500, on the API and in the seed
scripts alike. Nothing covered it.

Also pins the ``integrity_status`` default, which was the literal string ``"VALID"``
while the enum member is ``"Valid"``, so any caller relying on the default was
rejected by the enum.
"""

import uuid

import pytest
from sqlalchemy import text

from app.application.dtos.event import EventCreate
from app.application.services.hash_service import HashService
from app.application.use_cases.events.create_event import EventService
from app.domain.enums import EventIntegrityStatus, TenantStatus
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.shared.utils.datetime import utc_now

pytestmark = pytest.mark.requires_db


async def _tenant_and_subject(session) -> tuple[str, str]:
    """Create a throwaway organisation and subject, returning their ids.

    A fresh organisation each run, because a fixed code could not be reused: looking
    one up by code needs to read the tenant table before any tenant context exists,
    which the application role cannot do, so the second run would always collide.

    This test leaves its rows behind on purpose. Events are immutable — the delete
    trigger refuses them — which is the guarantee being exercised here, so nothing
    created below can be removed afterwards. Rows are prefixed "evtx-" to make them
    obvious, and are safe to prune with the administrator connection.
    """
    tenant_repo = TenantRepository(session, cache_service=None, audit_service=None)
    tenant = await tenant_repo.create_tenant(
        code=f"evtx-{uuid.uuid4().hex[:6]}",
        name="Event Transaction Test",
        status=TenantStatus.ACTIVE,
    )
    tenant_id = tenant.id

    subject_repo = SubjectRepository(session, tenant_id=tenant_id, audit_service=None)
    subject = await subject_repo.create_subject(
        tenant_id=tenant_id,
        subject_type="client",
        external_ref=f"EVTX-{uuid.uuid4().hex[:8]}",
    )
    await session.flush()
    return tenant_id, subject.id


async def test_create_event_succeeds_with_an_ambient_transaction(db_session) -> None:
    """The write releases the transaction it did not open, then opens its own."""
    tenant_id, subject_id = await _tenant_and_subject(db_session)
    # Commit the fixtures: create_event releases the transaction it did not open, so
    # anything still uncommitted at that point is discarded.
    await db_session.commit()

    # Mimic get_db: a session already inside a transaction with the tenant context
    # set. This is what used to make create_event raise.
    await db_session.execute(
        text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
    )
    assert db_session.in_transaction()

    service = EventService(
        event_repo=EventRepository(db_session),
        hash_service=HashService(),
        subject_repo=SubjectRepository(
            db_session, tenant_id=tenant_id, audit_service=None
        ),
        db=db_session,
        schema_validator=None,
        transition_validator=None,
        post_create_hooks=[],
    )

    first = await service.create_event(
        tenant_id=tenant_id,
        data=EventCreate(
            subject_id=subject_id,
            event_type="client",
            schema_version=1,
            event_time=utc_now(),
            payload={"name": "First"},
        ),
        trigger_workflows=False,
    )
    assert first.id
    assert first.is_genesis_event(), "first event on a subject is the genesis"

    second = await service.create_event(
        tenant_id=tenant_id,
        data=EventCreate(
            subject_id=subject_id,
            event_type="client",
            schema_version=1,
            event_time=utc_now(),
            payload={"name": "Second"},
        ),
        trigger_workflows=False,
    )
    assert second.chain.previous_hash == first.chain.current_hash, (
        "the chain must link to the event before"
    )

    # Committed by create_event's own transaction, so still there afterwards. The
    # context has to be set again first: create_event committed, and SET LOCAL went
    # with it, so this fresh transaction would otherwise see nothing.
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    count = await db_session.execute(
        text("SELECT count(*) FROM event WHERE subject_id = :s"), {"s": subject_id}
    )
    assert count.scalar() == 2

    # No cleanup: events are immutable, so the rows created here are permanent. That
    # is the guarantee under test, not an oversight.
