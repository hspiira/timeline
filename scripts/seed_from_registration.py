"""Seed from tenant registration through to events with a single dummy password.

Flow (see docs/SEED_FROM_REGISTRATION_FLOW.md):
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
Requires: DATABASE_BACKEND=postgres, migrations applied.
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
from app.core.config import get_settings
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


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
    load_dotenv(_project_root() / ".env", override=True)


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


async def run(path: Path) -> None:
    _load_env()
    if not path.exists():
        print(f"Seed file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        data = json.load(f)
    seed_password = data.get("seed_password", "SeedPassword1!")
    tenants_data = data.get("tenants", [])
    event_schemas_data = data.get("event_schemas", [])
    event_transition_rules_data = data.get("event_transition_rules", [])
    subjects_data = data.get("subjects", [])
    users_data = data.get("users", [])
    workflows_data = data.get("workflows", [])
    events_data = data.get("events", [])

    settings = get_settings()
    if settings.database_backend != "postgres":
        print("This script requires DATABASE_BACKEND=postgres", file=sys.stderr)
        sys.exit(1)
    _ensure_engine()
    if db_mod.AsyncSessionLocal is None:
        print(
            "AsyncSessionLocal not configured. Set DATABASE_URL and run: uv run alembic upgrade head",
            file=sys.stderr,
        )
        sys.exit(1)

    async with db_mod.AsyncSessionLocal() as session:
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

            tenant_ids: dict[str, str] = {}
            for t in tenants_data:
                code = t["code"]
                tenant_id = await _get_or_create_tenant(
                    session,
                    tenant_repo,
                    init_svc,
                    code=code,
                    name=t["name"],
                    status=t.get("status", "active"),
                )
                tenant_ids[code] = tenant_id
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
                print(f"  Admin user ensured (password from seed)")

            for es in event_schemas_data:
                tenant_id = tenant_ids.get(es["tenant_code"])
                if not tenant_id:
                    continue
                next_ver = await schema_repo.get_next_version(
                    tenant_id, es["event_type"]
                )
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

            transition_rule_repo = EventTransitionRuleRepository(session)
            for tr in event_transition_rules_data:
                tenant_id = tenant_ids.get(tr["tenant_code"])
                if not tenant_id:
                    continue
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
                print(f"  Transition rule {tr['event_type']} -> required prior: {tr['required_prior_event_types']}")

            subject_ids: dict[tuple[str, str], str] = {}
            for sub in subjects_data:
                tenant_id = tenant_ids.get(sub["tenant_code"])
                if not tenant_id:
                    continue
                ref = sub.get("external_ref")
                subject_repo = SubjectRepository(
                    session, tenant_id=tenant_id, audit_service=None
                )
                existing_sub = await subject_repo.get_by_external_ref(
                    tenant_id, ref or ""
                )
                if existing_sub:
                    key = (tenant_id, ref or "")
                    subject_ids[key] = existing_sub.id
                    print(f"  Subject {ref} already exists, skip")
                    continue
                created = await subject_repo.create_subject(
                    tenant_id=tenant_id,
                    subject_type=sub["subject_type"],
                    external_ref=ref,
                )
                key = (tenant_id, created.external_ref or "")
                subject_ids[key] = created.id
                print(f"  Subject {created.external_ref} ({created.subject_type}) -> {created.id}")

            for u in users_data:
                tenant_id = tenant_ids.get(u["tenant_code"])
                if not tenant_id:
                    continue
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

            for w in workflows_data:
                tenant_id = tenant_ids.get(w["tenant_code"])
                if not tenant_id:
                    continue
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

            for ev in events_data:
                tenant_id = tenant_ids.get(ev["tenant_code"])
                if not tenant_id:
                    continue
                subject_id = subject_ids.get(
                    (tenant_id, ev["subject_external_ref"])
                )
                if not subject_id:
                    print(
                        f"  Skip event: subject {ev['subject_external_ref']} not found"
                    )
                    continue
                event_repo = EventRepository(session)
                hash_service = HashService()
                subject_repo = SubjectRepository(
                    session, tenant_id=tenant_id, audit_service=None
                )
                schema_validator = EventSchemaValidator(schema_repo)
                event_svc = EventService(
                    event_repo=event_repo,
                    hash_service=hash_service,
                    subject_repo=subject_repo,
                    schema_validator=schema_validator,
                    workflow_engine_provider=lambda: None,
                )
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
                    print(f"  Event {ev['event_type']} on {ev['subject_external_ref']} -> {created.id}")
                except Exception as e:
                    print(
                        f"  Skip event {ev['event_type']} on {ev['subject_external_ref']}: {e}",
                        file=sys.stderr,
                    )

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
