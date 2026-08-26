"""Adversarial tests for the guarantee the product is sold on: that a stored
timeline cannot be altered without the alteration being apparent.

The happy path is covered elsewhere. These exercise the cases an attacker or a bug
would actually take: editing a stored event, and racing two writers at one subject
so the chain forks into two branches that each look valid on their own.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.application.dtos.event import EventCreate
from app.application.services.hash_service import HashService
from app.application.services.verification_service import VerificationService
from app.application.use_cases.events.create_event import EventService
from app.domain.enums import TenantStatus
from app.infrastructure.persistence import database as _database
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.shared.utils.datetime import utc_now

pytestmark = pytest.mark.requires_db

IMMUTABILITY_TRIGGER = "prevent_event_update_delete"


async def _tenant_and_subject(session) -> tuple[str, str]:
    """Create a throwaway organisation and subject, returning their ids.

    Rows are left behind deliberately. Events cannot be deleted, which is the
    property under test, so nothing created here can be cleaned up afterwards.
    The "chain-" prefix marks them for pruning with the administrator connection.
    """
    tenant_repo = TenantRepository(session, cache_service=None, audit_service=None)
    tenant = await tenant_repo.create_tenant(
        code=f"chain-{uuid.uuid4().hex[:6]}",
        name="Chain Integrity Test",
        status=TenantStatus.ACTIVE,
    )
    subject_repo = SubjectRepository(session, tenant_id=tenant.id, audit_service=None)
    subject = await subject_repo.create_subject(
        tenant_id=tenant.id,
        subject_type="client",
        external_ref=f"CHAIN-{uuid.uuid4().hex[:8]}",
    )
    await session.flush()
    return tenant.id, subject.id


def _event_service(session, tenant_id: str) -> EventService:
    """Build an EventService against one session, with the optional stages off.

    Schema validation, workflows and epochs are irrelevant to chain linkage and
    would only add setup that could fail for unrelated reasons.
    """
    return EventService(
        event_repo=EventRepository(session),
        hash_service=HashService(),
        subject_repo=SubjectRepository(session, tenant_id=tenant_id, audit_service=None),
        db=session,
        schema_validator=None,
        transition_validator=None,
        post_create_hooks=[],
    )


async def _append(service: EventService, tenant_id: str, subject_id: str, name: str):
    """Append one event carrying a distinguishable payload."""
    return await service.create_event(
        tenant_id=tenant_id,
        data=EventCreate(
            subject_id=subject_id,
            event_type="client",
            schema_version=1,
            event_time=utc_now(),
            payload={"name": name},
        ),
        trigger_workflows=False,
    )


async def test_the_database_refuses_to_alter_a_stored_event(db_session) -> None:
    """An event cannot be updated or deleted, even by the application's own role.

    Verification would catch an edit after the fact; this trigger means an ordinary
    application compromise cannot make the edit in the first place.
    """
    tenant_id, subject_id = await _tenant_and_subject(db_session)
    await db_session.commit()

    service = _event_service(db_session, tenant_id)
    event = await _append(service, tenant_id, subject_id, "Original")

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))

    with pytest.raises(DatabaseError):
        await db_session.execute(
            text("UPDATE event SET payload = '{\"name\": \"Edited\"}'::jsonb WHERE id = :i"),
            {"i": event.id},
        )
    await db_session.rollback()

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    with pytest.raises(DatabaseError):
        await db_session.execute(
            text("DELETE FROM event WHERE id = :i"), {"i": event.id}
        )
    await db_session.rollback()


async def test_verification_reports_an_event_edited_behind_the_trigger(db_session) -> None:
    """Verification detects a payload edit made by someone who could bypass the trigger.

    The trigger stops the application; it does not stop an operator with rights over
    the table. That is the threat the hash chain exists for, so the edit is made here
    the only way it could really be made, by disabling the trigger first.

    Skips unless the connected role may disable the trigger, which the restricted
    application role deliberately cannot.
    """
    tenant_id, subject_id = await _tenant_and_subject(db_session)
    await db_session.commit()

    service = _event_service(db_session, tenant_id)
    first = await _append(service, tenant_id, subject_id, "First")
    await _append(service, tenant_id, subject_id, "Second")

    try:
        await db_session.execute(
            text(f"ALTER TABLE event DISABLE TRIGGER {IMMUTABILITY_TRIGGER}")
        )
    except DatabaseError:
        await db_session.rollback()
        pytest.skip(
            "Connected role cannot disable the immutability trigger, so an edit "
            "cannot be staged. Run as the table owner to exercise this test."
        )

    try:
        await db_session.execute(
            text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
        )
        await db_session.execute(
            text("UPDATE event SET payload = '{\"name\": \"Tampered\"}'::jsonb WHERE id = :i"),
            {"i": first.id},
        )
        await db_session.commit()
    finally:
        await db_session.execute(
            text(f"ALTER TABLE event ENABLE TRIGGER {IMMUTABILITY_TRIGGER}")
        )
        await db_session.commit()

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    verifier = VerificationService(
        event_repo=EventRepository(db_session), hash_service=HashService()
    )
    result = await verifier.verify_subject_chain(subject_id, tenant_id)

    assert not result.is_chain_valid, "an edited payload must invalidate the chain"
    assert result.invalid_events >= 1
    broken = [r for r in result.event_results if not r.is_valid]
    assert any(r.event_id == first.id for r in broken), (
        "the edited event itself must be reported, not only its successor"
    )


async def test_concurrent_appends_to_one_subject_do_not_fork_the_chain(db_session) -> None:
    """Two writers racing at the same subject produce one chain, not two branches.

    Nothing in the schema enforces this. There is no unique constraint on
    (subject_id, previous_hash), so the invariant rests entirely on the
    ``SELECT ... FOR UPDATE`` taken against the subject row before the previous hash
    is read. If that lock is ever dropped or narrowed, two events will link to the
    same parent, both will verify in isolation, and this is what will notice.
    """
    tenant_id, subject_id = await _tenant_and_subject(db_session)
    await db_session.commit()

    # Separate sessions: two writers on one connection would serialise trivially and
    # the lock would never be contended.
    async with _database.AsyncSessionLocal() as session_a, \
            _database.AsyncSessionLocal() as session_b:
        results = await asyncio.gather(
            _append(_event_service(session_a, tenant_id), tenant_id, subject_id, "A"),
            _append(_event_service(session_b, tenant_id), tenant_id, subject_id, "B"),
            return_exceptions=True,
        )

    failures = [r for r in results if isinstance(r, BaseException)]
    assert not failures, f"both appends should succeed, got: {failures}"

    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    events = await EventRepository(db_session).get_by_subject(
        subject_id, tenant_id, skip=0, limit=100
    )
    assert len(events) == 2

    ordered = sorted(events, key=lambda e: e.event_seq)
    assert ordered[0].previous_hash is None, "the first event starts the chain"
    assert ordered[1].previous_hash == ordered[0].hash, (
        "the second event must link to the first, not to the same parent"
    )

    parents = [e.previous_hash for e in ordered]
    assert len(parents) == len(set(parents)), (
        "two events sharing a parent is a fork: the chain has branched"
    )

    verifier = VerificationService(
        event_repo=EventRepository(db_session), hash_service=HashService()
    )
    result = await verifier.verify_subject_chain(subject_id, tenant_id)
    assert result.is_chain_valid
