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
from app.infrastructure.persistence.database import AsyncSessionLocal, _ensure_engine
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
from app.infrastructure.services.tenant_initialization_service import (
    TenantInitializationService,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
    """Load .env from project root so get_settings() sees DATABASE_* when run as script."""
    load_dotenv(_project_root() / ".env", override=True)


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


async def run(path: Path) -> None:
    _load_env()
    if not path.exists():
        print(f"Seed file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        data = json.load(f)
    tenants_data = data.get("tenants", [])
    event_schemas_data = data.get("event_schemas", [])
    subjects_data = data.get("subjects", [])
    users_data = data.get("users", [])
    workflows_data = data.get("workflows", [])
    events_data = data.get("events", [])

    _ensure_engine()
    from app.infrastructure.persistence import database as db_mod
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
            schema_repo = EventSchemaRepository(
                session, cache_service=None, audit_service=None
            )
            role_repo = RoleRepository(session, audit_service=None)
            user_repo = UserRepository(session, audit_service=None)
            user_role_repo = UserRoleRepository(session, audit_service=None)
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

            subject_ids: dict[tuple[str, str], str] = {}
            for sub in subjects_data:
                tenant_id = tenant_ids.get(sub["tenant_code"])
                if not tenant_id:
                    continue
                ref = sub.get("external_ref")
                subject_repo = SubjectRepository(
                    session, tenant_id=tenant_id, audit_service=None
                )
                try:
                    created = await subject_repo.create_subject(
                        tenant_id=tenant_id,
                        subject_type=sub["subject_type"],
                        external_ref=ref,
                    )
                except Exception as e:
                    if "uq_subject_tenant_external_ref" in str(e) or "unique" in str(e).lower():
                        existing = await subject_repo.get_by_external_ref(
                            tenant_id, ref or ""
                        )
                        if existing:
                            created = existing
                            key = (tenant_id, ref or "")
                            subject_ids[key] = created.id
                        print(f"  Subject {ref} already exists, skip")
                        continue
                    raise
                else:
                    key = (tenant_id, created.external_ref or "")
                    subject_ids[key] = created.id
                    print(f"  Subject {created.external_ref} ({created.subject_type}) -> {created.id}")

            for u in users_data:
                tenant_id = tenant_ids.get(u["tenant_code"])
                if not tenant_id:
                    continue
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
                    if "uq_tenant_username" in str(e) or "unique" in str(e).lower():
                        print(f"  User {u['username']} already exists, skip")
                    else:
                        raise

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
