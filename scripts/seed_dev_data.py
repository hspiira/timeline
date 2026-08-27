"""Seed dev data from docs/seed-data.json into Postgres.

Loads tenants (by code; creates if missing), event_schemas, subjects, users
(with hashed password), workflows, and events (via EventService for hash chaining).
References: docs/seed-data.json, docs/DATABASE_SCHEMA.md.

Usage:
    uv run python -m scripts.seed_dev_data [path/to/seed-data.json]

Default path: docs/seed-data.json (relative to project root).
Requires: DATABASE_URL (Postgres), existing DB. Tenants are created if not found.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event import EventCreate
from app.application.services.event_schema_validator import EventSchemaValidator
from app.application.services.hash_service import HashService
from app.application.use_cases.events.create_event import EventService
from app.core.config import get_settings
from app.domain.enums import TenantStatus
from app.infrastructure.persistence.database import _ensure_engine
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.event_schema_repo import (
    EventSchemaRepository,
)
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.persistence.repositories.user_role_repo import (
    UserRoleRepository,
)
from app.infrastructure.persistence.repositories.workflow_repo import WorkflowRepository
from scripts._session import use_tenant, use_tenant_for_connection
from app.infrastructure.services.tenant_initialization_service import (
    TenantInitializationService,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
    """Load .env from project root so get_settings() sees DATABASE_* when run as script."""
    # override=False so an explicitly set DATABASE_URL wins over .env. With
    # override=True these scripts silently ignored the administrator connection
    # string they are meant to be run with, reconnecting as the application role
    # and then failing to see any existing tenant.
    load_dotenv(_project_root() / ".env", override=False)


def _parse_event_time(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _get_or_create_tenant(
    session: AsyncSession,
    tenant_repo: TenantRepository,
    init_svc: TenantInitializationService,
    code: str,
    name: str,
    status: str,
) -> str:
    existing = await tenant_repo.get_by_code(code)
    if existing:
        return existing.id
    tenant = await tenant_repo.create_tenant(
        code=code,
        name=name,
        status=TenantStatus(status),
    )
    await init_svc.initialize_tenant_infrastructure(tenant_id=tenant.id)
    return tenant.id


def _load_seed_file(path: Path) -> dict:
    """Read the seed JSON, or exit with a message if it is not there."""
    if not path.exists():
        print(f"Seed file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return json.load(f)


def _session_factory_or_exit():
    """Return the configured session factory, or exit explaining what is missing."""
    _ensure_engine()
    from app.infrastructure.persistence import database as db_mod

    if db_mod.AsyncSessionLocal is None:
        print(
            "AsyncSessionLocal not configured. Set DATABASE_URL and run: uv run alembic upgrade head",
            file=sys.stderr,
        )
        sys.exit(1)
    return db_mod.AsyncSessionLocal


async def _seed_tenants(
    session: AsyncSession,
    tenant_repo: TenantRepository,
    init_svc: TenantInitializationService,
    tenants_data: list[dict],
) -> dict[str, str]:
    """Create the tenants that do not exist yet. Returns code -> tenant id."""
    tenant_ids: dict[str, str] = {}
    for t in tenants_data:
        code = t["code"]
        tenant_id = await _get_or_create_tenant(
            session,
            tenant_repo,
            init_svc,
            code=code,
            name=t["name"],
            status=t.get("status", TenantStatus.ACTIVE.value),
        )
        tenant_ids[code] = tenant_id
        # create_tenant() sets this for a new tenant, but an existing
        # one returns early, so set it for both cases.
        await use_tenant(session, tenant_id)
        print(f"Tenant {code} -> {tenant_id}")
    return tenant_ids


async def _seed_event_schemas(
    session: AsyncSession,
    schema_repo: EventSchemaRepository,
    tenant_ids: dict[str, str],
    event_schemas_data: list[dict],
) -> None:
    """Create version 1 of each event schema that has no versions yet."""
    for es in event_schemas_data:
        tenant_id = tenant_ids.get(es["tenant_code"])
        if not tenant_id:
            continue
        # Row-level security is keyed on this; without it the writes below
        # are rejected and the reads silently return nothing.
        await use_tenant(session, tenant_id)
        next_ver = await schema_repo.get_next_version(tenant_id, es["event_type"])
        if next_ver > 1:
            print(f"  Event schema {es['event_type']} already exists, skip")
            continue
        await schema_repo.create_schema(
            tenant_id=tenant_id,
            event_type=es["event_type"],
            schema_definition=es["schema_definition"],
            is_active=es.get("is_active", True),
            created_by=None,
        )
        print(f"  Event schema {es['event_type']}@v1 for {es['tenant_code']}")


def _is_duplicate_error(exc: Exception, constraint: str) -> bool:
    """Whether this exception is the unique-constraint violation we expect."""
    text = str(exc)
    return constraint in text or "unique" in text.lower()


async def _seed_one_subject(
    session: AsyncSession,
    tenant_id: str,
    sub: dict,
    subject_ids: dict[tuple[str, str], str],
) -> None:
    """Create one subject, tolerating one that is already present."""
    ref = sub.get("external_ref")
    subject_repo = SubjectRepository(session, tenant_id=tenant_id, audit_service=None)
    try:
        created = await subject_repo.create_subject(
            tenant_id=tenant_id,
            subject_type=sub["subject_type"],
            external_ref=ref,
        )
    except Exception as e:
        if not _is_duplicate_error(e, "uq_subject_tenant_external_ref"):
            raise
        existing = await subject_repo.get_by_external_ref(tenant_id, ref or "")
        if existing:
            subject_ids[(tenant_id, ref or "")] = existing.id
        print(f"  Subject {ref} already exists, skip")
        return
    subject_ids[(tenant_id, created.external_ref or "")] = created.id
    print(
        f"  Subject {created.external_ref} ({created.subject_type}) -> {created.id}"
    )


async def _seed_subjects(
    session: AsyncSession,
    tenant_ids: dict[str, str],
    subjects_data: list[dict],
) -> dict[tuple[str, str], str]:
    """Create the subjects. Returns (tenant id, external ref) -> subject id."""
    subject_ids: dict[tuple[str, str], str] = {}
    for sub in subjects_data:
        tenant_id = tenant_ids.get(sub["tenant_code"])
        if not tenant_id:
            continue
        # Row-level security is keyed on this; without it the writes below
        # are rejected and the reads silently return nothing.
        await use_tenant(session, tenant_id)
        await _seed_one_subject(session, tenant_id, sub, subject_ids)
    return subject_ids


async def _seed_one_user(
    tenant_id: str,
    u: dict,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    user_role_repo: UserRoleRepository,
) -> None:
    """Create one user and give them the agent role, tolerating a duplicate."""
    try:
        user = await user_repo.create_user(
            tenant_id=tenant_id,
            username=u["username"],
            email=u["email"],
            password=u["password"],
        )
        role = await role_repo.get_by_code_and_tenant("agent", tenant_id)
        if role:
            await user_role_repo.assign_role_to_user(
                user_id=user.id,
                role_id=role.id,
                tenant_id=tenant_id,
                assigned_by=user.id,
            )
        print(f"  User {u['username']} -> {user.id}")
    except Exception as e:
        if not _is_duplicate_error(e, "uq_tenant_username"):
            raise
        print(f"  User {u['username']} already exists, skip")


async def _seed_users(
    session: AsyncSession,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    user_role_repo: UserRoleRepository,
    tenant_ids: dict[str, str],
    users_data: list[dict],
) -> None:
    """Create the users listed in the seed file."""
    for u in users_data:
        tenant_id = tenant_ids.get(u["tenant_code"])
        if not tenant_id:
            continue
        # Row-level security is keyed on this; without it the writes below
        # are rejected and the reads silently return nothing.
        await use_tenant(session, tenant_id)
        await _seed_one_user(tenant_id, u, user_repo, role_repo, user_role_repo)


async def _seed_workflows(
    session: AsyncSession,
    workflow_repo: WorkflowRepository,
    tenant_ids: dict[str, str],
    workflows_data: list[dict],
) -> None:
    """Create the workflows listed in the seed file."""
    for w in workflows_data:
        tenant_id = tenant_ids.get(w["tenant_code"])
        if not tenant_id:
            continue
        # Row-level security is keyed on this; without it the writes below
        # are rejected and the reads silently return nothing.
        await use_tenant(session, tenant_id)
        await workflow_repo.create_workflow(
            tenant_id=tenant_id,
            name=w["name"],
            trigger_event_type=w["trigger_event_type"],
            actions=w["actions"],
            description=w.get("description"),
            is_active=w.get("is_active", True),
            trigger_conditions=w.get("trigger_conditions"),
            max_executions_per_day=w.get("max_executions_per_day"),
            execution_order=w.get("execution_order", 0),
        )
        print(f"  Workflow {w['name']}")


def _build_event_service(event_session: AsyncSession, tenant_id: str) -> EventService:
    """An EventService bound to the given session and tenant."""
    return EventService(
        event_repo=EventRepository(event_session),
        hash_service=HashService(),
        subject_repo=SubjectRepository(
            event_session, tenant_id=tenant_id, audit_service=None
        ),
        db=event_session,
        schema_validator=EventSchemaValidator(
            EventSchemaRepository(
                event_session, cache_service=None, audit_service=None
            )
        ),
        post_create_hooks=[],
    )


async def _seed_one_event(
    event_session: AsyncSession, tenant_id: str, subject_id: str, ev: dict
) -> None:
    """Create one event through EventService so it joins the hash chain."""
    event_svc = _build_event_service(event_session, tenant_id)
    cmd = EventCreate(
        subject_id=subject_id,
        event_type=ev["event_type"],
        schema_version=ev["schema_version"],
        event_time=_parse_event_time(ev["event_time"]),
        payload=ev.get("payload", {}),
    )
    try:
        created = await event_svc.create_event(
            tenant_id=tenant_id, data=cmd, trigger_workflows=False
        )
        print(
            f"  Event {ev['event_type']} on "
            f"{ev['subject_external_ref']} -> {created.id}"
        )
    except Exception as e:
        print(
            f"  Skip event {ev['event_type']} on "
            f"{ev['subject_external_ref']}: {e}",
            file=sys.stderr,
        )


def _resolve_event_target(
    ev: dict,
    tenant_ids: dict[str, str],
    subject_ids: dict[tuple[str, str], str],
) -> tuple[str, str] | None:
    """Resolve an event's tenant and subject, or None if either is unknown."""
    tenant_id = tenant_ids.get(ev["tenant_code"])
    if not tenant_id:
        return None
    subject_id = subject_ids.get((tenant_id, ev["subject_external_ref"]))
    if not subject_id:
        print(f"  Skip event: subject {ev['subject_external_ref']} not found")
        return None
    return tenant_id, subject_id


async def _seed_events(
    session_factory,
    tenant_ids: dict[str, str],
    subject_ids: dict[tuple[str, str], str],
    events_data: list[dict],
) -> None:
    """Create the events on their own session, after the seeding transaction committed.

    EventService opens a transaction per event so it can lock the subject row and
    retry on a chain fork, which it cannot do nested inside an outer transaction.
    """
    async with session_factory() as event_session:
        current_tenant: str | None = None
        for ev in events_data:
            target = _resolve_event_target(ev, tenant_ids, subject_ids)
            if target is None:
                continue
            tenant_id, subject_id = target
            # Connection-scoped, so EventService's own transactions inherit it.
            if tenant_id != current_tenant:
                await use_tenant_for_connection(event_session, tenant_id)
                current_tenant = tenant_id
            await _seed_one_event(event_session, tenant_id, subject_id, ev)


async def run(path: Path) -> None:
    _load_env()
    data = _load_seed_file(path)
    session_factory = _session_factory_or_exit()

    async with session_factory() as session:
        async with session.begin():
            tenant_repo = TenantRepository(
                session, cache_service=None, audit_service=None
            )
            init_svc = TenantInitializationService(session)
            schema_repo = EventSchemaRepository(
                session, cache_service=None, audit_service=None
            )
            role_repo = RoleRepository(session, audit_service=None)
            user_repo = UserRepository(session, audit_service=None)
            user_role_repo = UserRoleRepository(session, audit_service=None)
            workflow_repo = WorkflowRepository(session, audit_service=None)

            tenant_ids = await _seed_tenants(
                session, tenant_repo, init_svc, data.get("tenants", [])
            )
            await _seed_event_schemas(
                session, schema_repo, tenant_ids, data.get("event_schemas", [])
            )
            subject_ids = await _seed_subjects(
                session, tenant_ids, data.get("subjects", [])
            )
            await _seed_users(
                session,
                user_repo,
                role_repo,
                user_role_repo,
                tenant_ids,
                data.get("users", []),
            )
            await _seed_workflows(
                session, workflow_repo, tenant_ids, data.get("workflows", [])
            )

    # Events run after the transaction above has committed, on their own session.
    events_data = data.get("events", [])
    if events_data:
        await _seed_events(session_factory, tenant_ids, subject_ids, events_data)

    print("Seed completed.")



def main() -> None:
    root = _project_root()
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = Path(path_arg) if path_arg else root / "scripts" / "seed-data.json"
    if not path.is_absolute():
        path = (root / path).resolve()
    asyncio.run(run(path))


if __name__ == "__main__":
    main()
