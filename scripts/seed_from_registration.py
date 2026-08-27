"""Seed from tenant registration through to events with a single dummy password.

Flow (see docs/RUNBOOKS.md §5 Seed from registration):
  1. Tenant registration: create tenant + RBAC init + admin user (dummy password) + assign admin role.
  2. Event schemas (by tenant_code, event_type).
  3. Event transition rules (by tenant_code, event_type).
  4. Subjects (by tenant_code, external_ref).
  5. Additional users (dummy password, agent role).
  6. Workflows (by tenant_code, trigger_event_type).
  7. Events (by tenant_code, subject_external_ref, event_type; hash-chained via EventService).

All users share one password from the seed file (e.g. SeedPassword1!); the repository
hashes it on create. No random generation.

Usage:
    uv run python -m scripts.seed_from_registration [path/to/seed-from-registration.json]

Default path: scripts/seed-from-registration.json.
Requires: DATABASE_URL (Postgres), migrations applied.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from app.application.dtos.event import EventCreate
from app.application.services.event_schema_validator import EventSchemaValidator
from app.application.services.hash_service import HashService
from app.application.use_cases.events.create_event import EventService
from app.domain.enums import TenantStatus
from app.infrastructure.persistence import database as db_mod
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
from app.infrastructure.persistence.repositories.event_transition_rule_repo import (
    EventTransitionRuleRepository,
)
from app.infrastructure.services.tenant_initialization_service import (
    TenantInitializationService,
)
from scripts._session import use_tenant, use_tenant_for_connection


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
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
    session,
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


async def _ensure_admin_user(
    session,
    tenant_id: str,
    tenant_code: str,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    user_role_repo: UserRoleRepository,
    init_svc: TenantInitializationService,
    password: str,
) -> None:
    admin_username = "admin"
    existing = await user_repo.get_by_username_and_tenant(admin_username, tenant_id)
    if existing:
        return
    admin_user = await user_repo.create_user(
        tenant_id=tenant_id,
        username=admin_username,
        email=f"admin@{tenant_code}.timeline",
        password=password,
    )
    await init_svc.assign_admin_role(
        tenant_id=tenant_id,
        admin_user_id=admin_user.id,
    )


def _load_seed_file(path: Path) -> dict:
    """Read the seed JSON, or exit with a message if it is not there."""
    if not path.exists():
        print(f"Seed file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return json.load(f)


def _require_session_factory():
    """Return the configured session factory, or exit explaining what is missing."""
    _ensure_engine()
    if db_mod.AsyncSessionLocal is None:
        print(
            "AsyncSessionLocal not configured. Set DATABASE_URL and run: uv run alembic upgrade head",
            file=sys.stderr,
        )
        sys.exit(1)
    return db_mod.AsyncSessionLocal


async def _register_tenants(
    session,
    tenant_repo: TenantRepository,
    init_svc: TenantInitializationService,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    user_role_repo: UserRoleRepository,
    tenants_data: list[dict],
    seed_password: str,
) -> dict[str, str]:
    """Step 1: register each tenant and ensure it has an admin user."""
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
        await use_tenant(session, tenant_id)
        print(f"Tenant {code} -> {tenant_id}")
        await _ensure_admin_user(
            session,
            tenant_id,
            code,
            user_repo,
            role_repo,
            user_role_repo,
            init_svc,
            seed_password,
        )
        print("  Admin user ensured (password from seed)")
    return tenant_ids


async def _seed_event_schemas(
    session,
    schema_repo: EventSchemaRepository,
    tenant_ids: dict[str, str],
    event_schemas_data: list[dict],
) -> None:
    """Step 2: create version 1 of each event schema that has no versions yet."""
    for es in event_schemas_data:
        tenant_id = tenant_ids.get(es["tenant_code"])
        if not tenant_id:
            continue
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


async def _seed_transition_rules(
    session,
    tenant_ids: dict[str, str],
    event_transition_rules_data: list[dict],
) -> None:
    """Step 3: create the event transition rules that do not exist yet."""
    transition_rule_repo = EventTransitionRuleRepository(session)
    for tr in event_transition_rules_data:
        tenant_id = tenant_ids.get(tr["tenant_code"])
        if not tenant_id:
            continue
        await use_tenant(session, tenant_id)
        existing_rule = await transition_rule_repo.get_rule_for_event_type(
            tenant_id, tr["event_type"]
        )
        if existing_rule:
            print(f"  Transition rule {tr['event_type']} already exists, skip")
            continue
        await transition_rule_repo.create_rule(
            tenant_id=tenant_id,
            event_type=tr["event_type"],
            required_prior_event_types=tr["required_prior_event_types"],
            description=tr.get("description"),
            prior_event_payload_conditions=tr.get("prior_event_payload_conditions"),
            max_occurrences_per_stream=tr.get("max_occurrences_per_stream"),
            fresh_prior_event_type=tr.get("fresh_prior_event_type"),
        )
        print(
            f"  Transition rule {tr['event_type']} -> required prior: {tr['required_prior_event_types']}"
        )


async def _seed_subjects(
    session,
    tenant_ids: dict[str, str],
    subjects_data: list[dict],
) -> dict[tuple[str, str], str]:
    """Step 4: create the subjects. Returns (tenant id, external ref) -> subject id."""
    subject_ids: dict[tuple[str, str], str] = {}
    for sub in subjects_data:
        tenant_id = tenant_ids.get(sub["tenant_code"])
        if not tenant_id:
            continue
        await use_tenant(session, tenant_id)
        ref = sub.get("external_ref")
        subject_repo = SubjectRepository(
            session, tenant_id=tenant_id, audit_service=None
        )
        existing_sub = await subject_repo.get_by_external_ref(tenant_id, ref or "")
        if existing_sub:
            subject_ids[(tenant_id, ref or "")] = existing_sub.id
            print(f"  Subject {ref} already exists, skip")
            continue
        created = await subject_repo.create_subject(
            tenant_id=tenant_id,
            subject_type=sub["subject_type"],
            external_ref=ref,
        )
        subject_ids[(tenant_id, created.external_ref or "")] = created.id
        print(
            f"  Subject {created.external_ref} ({created.subject_type}) -> {created.id}"
        )
    return subject_ids


async def _seed_users(
    session,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    user_role_repo: UserRoleRepository,
    tenant_ids: dict[str, str],
    users_data: list[dict],
    seed_password: str,
) -> None:
    """Step 5: create the additional users and give them the agent role."""
    for u in users_data:
        tenant_id = tenant_ids.get(u["tenant_code"])
        if not tenant_id:
            continue
        # Row-level security is keyed on this; without it the writes below
        # are rejected and the reads silently return nothing.
        await use_tenant(session, tenant_id)
        existing_user = await user_repo.get_by_username_and_tenant(
            u["username"], tenant_id
        )
        if existing_user:
            print(f"  User {u['username']} already exists, skip")
            continue
        user = await user_repo.create_user(
            tenant_id=tenant_id,
            username=u["username"],
            email=u["email"],
            password=seed_password,
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


async def _seed_workflows(
    session,
    workflow_repo: WorkflowRepository,
    tenant_ids: dict[str, str],
    workflows_data: list[dict],
) -> None:
    """Step 6: create the workflows listed in the seed file."""
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


def _build_event_service(event_session, tenant_id: str) -> EventService:
    """An EventService bound to the given session and tenant."""
    event_schema_repo = EventSchemaRepository(
        event_session, cache_service=None, audit_service=None
    )
    return EventService(
        event_repo=EventRepository(event_session),
        hash_service=HashService(),
        subject_repo=SubjectRepository(
            event_session, tenant_id=tenant_id, audit_service=None
        ),
        db=event_session,
        schema_validator=EventSchemaValidator(event_schema_repo),
        post_create_hooks=[],
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


async def _seed_one_event(event_session, tenant_id: str, subject_id: str, ev: dict) -> None:
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


async def _seed_events(
    session_factory,
    tenant_ids: dict[str, str],
    subject_ids: dict[tuple[str, str], str],
    events_data: list[dict],
) -> None:
    """Step 7: create the events on a session of their own.

    EventService opens a transaction per event so it can lock the subject row and
    retry on a chain fork, which it cannot do inside an outer transaction ("a
    transaction is already begun on this Session"). Before this, every event was
    skipped with that error and the seed quietly produced none.
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
    seed_password = data.get("seed_password", "SeedPassword1!")
    session_factory = _require_session_factory()

    async with session_factory() as session:
        async with session.begin():
            tenant_repo = TenantRepository(
                session, cache_service=None, audit_service=None
            )
            init_svc = TenantInitializationService(session)
            user_repo = UserRepository(session, audit_service=None)
            role_repo = RoleRepository(session, audit_service=None)
            user_role_repo = UserRoleRepository(session, audit_service=None)
            schema_repo = EventSchemaRepository(
                session, cache_service=None, audit_service=None
            )
            workflow_repo = WorkflowRepository(session, audit_service=None)

            tenant_ids = await _register_tenants(
                session,
                tenant_repo,
                init_svc,
                user_repo,
                role_repo,
                user_role_repo,
                data.get("tenants", []),
                seed_password,
            )
            await _seed_event_schemas(
                session, schema_repo, tenant_ids, data.get("event_schemas", [])
            )
            await _seed_transition_rules(
                session, tenant_ids, data.get("event_transition_rules", [])
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
                seed_password,
            )
            await _seed_workflows(
                session, workflow_repo, tenant_ids, data.get("workflows", [])
            )

    # Events are seeded after the transaction above has committed.
    events_data = data.get("events", [])
    if events_data:
        await _seed_events(session_factory, tenant_ids, subject_ids, events_data)

    print("Seed from registration completed.")



def main() -> None:
    root = _project_root()
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = (
        Path(path_arg)
        if path_arg
        else root / "scripts" / "seed-from-registration.json"
    )
    if not path.is_absolute():
        path = (root / path).resolve()
    asyncio.run(run(path))


if __name__ == "__main__":
    main()
