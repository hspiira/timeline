"""Event, verification, and event-schema dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.event_schema_validator import EventSchemaValidator
from app.application.services.event_transition_validator import EventTransitionValidator
from app.application.services.hash_service import HashService
from app.application.use_cases.events import EventService
from app.application.services.verification_service import (
    ChainVerificationResult,
    VerificationService,
)
from app.core.config import get_settings
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    EventRepository,
    EventSchemaRepository,
    EventTransitionRuleRepository,
)
from app.infrastructure.services import SystemAuditService
from app.infrastructure.services.workflow_notification_service import (
    LogOnlyNotificationService,
    WorkflowRecipientResolver,
)
from app.infrastructure.services.workflow_template_renderer import WorkflowTemplateRenderer
from app.infrastructure.persistence.repositories import (
    RoleRepository,
    SubjectRepository,
    SubjectTypeRepository,
    TaskRepository,
    WorkflowRepository,
)
from app.infrastructure.services import WorkflowEngine

from . import tenant
from . import db as db_deps


def _build_event_service_for_session(
    db: AsyncSession,
    tenant_id: str,
    audit_svc: SystemAuditService,
) -> EventService:
    """Build EventService with the given session (no workflow engine).

    For use when creating events in the same transaction (e.g. relationship service).
    """
    event_repo = EventRepository(db)
    hash_service = HashService()
    subject_repo = SubjectRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
    schema_repo = EventSchemaRepository(
        db, cache_service=None, audit_service=audit_svc
    )
    schema_validator = EventSchemaValidator(schema_repo)
    transition_rule_repo = EventTransitionRuleRepository(db)
    transition_validator = EventTransitionValidator(
        rule_repo=transition_rule_repo,
        event_repo=event_repo,
    )
    subject_type_repo = SubjectTypeRepository(db, audit_service=audit_svc)
    return EventService(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_validator=schema_validator,
        workflow_engine_provider=None,
        transition_validator=transition_validator,
        subject_type_repo=subject_type_repo,
    )


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
) -> EventService:
    """Build EventService with hash chaining, schema validation, and workflow engine."""
    audit_svc = SystemAuditService(db, HashService())
    event_repo = EventRepository(db)
    hash_service = HashService()
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)
    schema_repo = EventSchemaRepository(
        db, cache_service=None, audit_service=audit_svc
    )
    schema_validator = EventSchemaValidator(schema_repo)
    workflow_repo = WorkflowRepository(db, audit_service=audit_svc)
    transition_rule_repo = EventTransitionRuleRepository(db)
    transition_validator = EventTransitionValidator(
        rule_repo=transition_rule_repo,
        event_repo=event_repo,
    )

    workflow_engine_holder: list[WorkflowEngine | None] = [None]

    def get_workflow_engine() -> WorkflowEngine | None:
        return workflow_engine_holder[0]

    subject_type_repo = SubjectTypeRepository(db, audit_service=audit_svc)
    event_service = EventService(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_validator=schema_validator,
        workflow_engine_provider=get_workflow_engine,
        transition_validator=transition_validator,
        subject_type_repo=subject_type_repo,
    )
    notification_service = LogOnlyNotificationService()
    recipient_resolver = WorkflowRecipientResolver(db)
    template_renderer = WorkflowTemplateRenderer()
    task_repo = TaskRepository(db)
    role_repo = RoleRepository(db, audit_service=None)
    workflow_engine = WorkflowEngine(
        db,
        event_service,
        workflow_repo,
        notification_service=notification_service,
        recipient_resolver=recipient_resolver,
        template_renderer=template_renderer,
        task_repo=task_repo,
        role_repo=role_repo,
    )
    workflow_engine_holder[0] = workflow_engine
    return event_service


async def get_event_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventRepository:
    """Event repository for read operations (list, get by id)."""
    return EventRepository(db)


async def get_verification_service(
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
) -> VerificationService:
    """Verification service for event chain integrity (hash + previous_hash)."""
    settings = get_settings()
    return VerificationService(
        event_repo=event_repo,
        hash_service=HashService(),
        max_events=settings.verification_max_events,
        timeout_seconds=settings.verification_timeout_seconds,
    )


def get_verification_runner():
    """Return a callable that runs tenant verification with a fresh session and configured limits (for background jobs)."""
    async def run_verification_for_tenant(tenant_id: str) -> ChainVerificationResult:
        gen = get_db()
        try:
            session = await gen.__anext__()
        except StopAsyncIteration:
            await gen.aclose()
            raise RuntimeError("Failed to obtain database session")
        try:
            event_repo = EventRepository(session)
            settings = get_settings()
            svc = VerificationService(
                event_repo=event_repo,
                hash_service=HashService(),
                max_events=settings.verification_max_events,
                timeout_seconds=settings.verification_timeout_seconds,
            )
            return await svc.verify_tenant_chains(tenant_id=tenant_id)
        finally:
            await gen.aclose()

    return run_verification_for_tenant


async def get_event_schema_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventSchemaRepository:
    """Event schema repository for read operations."""
    return EventSchemaRepository(db, cache_service=None, audit_service=None)


async def get_event_schema_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> EventSchemaRepository:
    """Event schema repository for create/update (transactional)."""
    return EventSchemaRepository(
        db, cache_service=None, audit_service=audit_svc
    )


async def get_event_transition_rule_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventTransitionRuleRepository:
    """Event transition rule repository for read operations."""
    return EventTransitionRuleRepository(db)


async def get_event_transition_rule_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EventTransitionRuleRepository:
    """Event transition rule repository for create/update/delete (transactional)."""
    return EventTransitionRuleRepository(db)
