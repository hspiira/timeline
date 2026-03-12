"""Event, subject, document, flow, workflow, naming, and search dependencies (composition root).

Domain-level FastAPI Depends() factories. Depends on _core for db sessions,
tenant resolution, and system audit.
"""

from __future__ import annotations

from contextlib import aclosing
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.document_category_metadata_validator import (
    DocumentCategoryMetadataValidator,
)
from app.application.services.enrichment import (
    ActorEnricher,
    CorrelationEnricher,
    SourceEnricher,
)
from app.application.services.event_schema_validator import EventSchemaValidator
from app.application.services.epoch_service import EpochService
from app.application.services.event_transition_validator import EventTransitionValidator
from app.application.services.hash_service import HashService
from app.application.services.subject_type_schema_validator import (
    SubjectTypeSchemaValidator,
)
from app.application.services.verification_service import (
    ChainVerificationResult,
    VerificationService,
)
from app.application.use_cases.analytics import GetDashboardStatsUseCase
from app.application.use_cases.projections import (
    ProjectionManagementUseCase,
    QueryProjectionUseCase,
)
from app.application.use_cases.documents import (
    DocumentQueryService,
    DocumentUploadService,
    RunDocumentRetentionUseCase,
)
from app.application.interfaces.post_create_hooks import IPostCreateHook
from app.application.use_cases.events import EventService
from app.application.use_cases.flows import (
    CreateFlowUseCase,
    GetFlowDocumentComplianceUseCase,
)
from app.application.use_cases.search import SearchService
from app.application.use_cases.state import (
    CreateSubjectSnapshotUseCase,
    GetSubjectStateUseCase,
    RunSnapshotJobUseCase,
)
from app.application.use_cases.subjects import (
    SubjectErasureService,
    SubjectExportService,
    SubjectRelationshipService,
    SubjectService,
)
from app.core.config import get_settings
from app.core.projections import get_registry
from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.external.storage.protocol import StorageProtocol
from app.infrastructure.persistence.database import (
    get_db,
    get_db_transactional,
)
from app.infrastructure.persistence.repositories import (
    ChainAnchorRepository,
    ProjectionRepository,
    WebhookSubscriptionRepository,
    DocumentCategoryRepository,
    DocumentRepository,
    DocumentRequirementRepository,
    EventRepository,
    IntegrityEpochRepository,
    EventSchemaRepository,
    EventTransitionRuleRepository,
    FlowRepository,
    NamingTemplateRepository,
    RelationshipKindRepository,
    RoleRepository,
    SearchRepository,
    SubjectRelationshipRepository,
    SubjectRepository,
    SubjectSnapshotRepository,
    SubjectTypeRepository,
    TaskRepository,
    TenantRepository,
    WorkflowExecutionRepository,
    WorkflowRepository,
)
from app.infrastructure.services import SystemAuditService, WorkflowEngine
from app.infrastructure.services.post_create_hooks import (
    EventStreamBroadcastHook,
    WebhookDispatchHook,
    WorkflowTriggerHook,
)
from app.infrastructure.services.webhook_dispatcher import WebhookDispatcher
from app.infrastructure.services.workflow_notification_service import (
    LogOnlyNotificationService,
    WorkflowRecipientResolver,
)
from app.infrastructure.services.workflow_template_renderer import WorkflowTemplateRenderer

from . import _core

# ---------------------------------------------------------------------------
# Storage (shared by document; set on app.state in lifespan)
# ---------------------------------------------------------------------------

def _get_storage_from_request(request: Request) -> StorageProtocol:
    """Storage from app.state (set in lifespan); fallback to factory when missing (e.g. tests)."""
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        return StorageFactory.create_storage_service()
    return storage


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

DEFAULT_API_ENRICHERS = [
    CorrelationEnricher(),
    ActorEnricher(),
    SourceEnricher(),
]


@dataclass(frozen=True)
class _EventServiceStack:
    """Shared repo/validator stack for EventService (DRY across get_event_service, get_event_service_for_create, build_event_service_for_connector)."""

    event_repo: EventRepository
    hash_service: HashService
    subject_repo: SubjectRepository
    schema_validator: EventSchemaValidator
    transition_validator: EventTransitionValidator
    subject_type_repo: SubjectTypeRepository
    epoch_service: EpochService


def _build_event_service_stack(
    db: AsyncSession,
    tenant_id: str,
    audit_svc: SystemAuditService,
) -> _EventServiceStack:
    """Build shared EventService dependencies. Callers add workflow engine, enrichers, webhook, broadcaster as needed."""
    event_repo = EventRepository(db)
    hash_service = HashService()
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)
    schema_repo = EventSchemaRepository(db, cache_service=None, audit_service=audit_svc)
    schema_validator = EventSchemaValidator(schema_repo)
    transition_rule_repo = EventTransitionRuleRepository(db)
    transition_validator = EventTransitionValidator(
        rule_repo=transition_rule_repo,
        event_repo=event_repo,
    )
    subject_type_repo = SubjectTypeRepository(db, audit_service=audit_svc)
    tenant_repo = TenantRepository(db, cache_service=None, audit_service=audit_svc)
    epoch_repo = IntegrityEpochRepository(db)
    epoch_service = EpochService(epoch_repo=epoch_repo, tenant_repo=tenant_repo)
    return _EventServiceStack(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_validator=schema_validator,
        transition_validator=transition_validator,
        subject_type_repo=subject_type_repo,
        epoch_service=epoch_service,
    )


def build_event_service_for_session(
    db: AsyncSession,
    tenant_id: str,
    audit_svc: SystemAuditService,
) -> EventService:
    """Build EventService with the given session (no workflow engine).

    Used when creating events in the same transaction (e.g. subject relationship service).
    """
    stack = _build_event_service_stack(db, tenant_id, audit_svc)
    return EventService(
        event_repo=stack.event_repo,
        hash_service=stack.hash_service,
        subject_repo=stack.subject_repo,
        db=db,
        schema_validator=stack.schema_validator,
        transition_validator=stack.transition_validator,
        subject_type_repo=stack.subject_type_repo,
        post_create_hooks=[],
        epoch_service=stack.epoch_service,
    )


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> EventService:
    """Build EventService with hash chaining, schema validation, and workflow engine."""
    stack = _build_event_service_stack(db, tenant_id, audit_svc)
    # Mutable cell to break circular init: EventService needs engine, engine needs EventService.
    workflow_engine_holder: list[WorkflowEngine | None] = [None]

    def get_workflow_engine() -> WorkflowEngine | None:
        return workflow_engine_holder[0]

    workflow_repo = WorkflowRepository(db, audit_service=audit_svc)
    event_service = EventService(
        event_repo=stack.event_repo,
        hash_service=stack.hash_service,
        subject_repo=stack.subject_repo,
        db=db,
        schema_validator=stack.schema_validator,
        transition_validator=stack.transition_validator,
        subject_type_repo=stack.subject_type_repo,
        enrichers=DEFAULT_API_ENRICHERS,
        post_create_hooks=[WorkflowTriggerHook(get_workflow_engine)],
        epoch_service=stack.epoch_service,
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


def build_event_service_for_connector(
    db: AsyncSession,
    tenant_id: str,
    app: FastAPI | None = None,
) -> EventService:
    """Build EventService for connector/background use (no request context).

    Same composition as get_event_service_for_create but sync; no workflow
    engine (connectors use trigger_workflows=False). Used by ConnectorRunner.
    When app is provided, wires webhook_dispatcher (shared http_client) and
    event_stream_broadcaster so connector-ingested events trigger webhooks and SSE.
    """
    from app.infrastructure.services import SystemAuditService

    audit_svc = SystemAuditService(db, HashService())
    stack = _build_event_service_stack(db, tenant_id, audit_svc)

    post_create_hooks: list[IPostCreateHook] = []
    if app is not None:
        state = getattr(app, "state", None)
        if state is not None:
            oauth_http_client = getattr(state, "oauth_http_client", None)
            event_stream_broadcaster = getattr(
                state, "event_stream_broadcaster", None
            )
            webhook_repo = WebhookSubscriptionRepository(db)
            webhook_dispatcher = WebhookDispatcher(
                webhook_repo.get_active_by_tenant,
                http_client=oauth_http_client,
            )
            pending_webhook_tasks = getattr(state, "pending_webhook_tasks", None)
            post_create_hooks = [
                WebhookDispatchHook(webhook_dispatcher, pending_webhook_tasks),
                EventStreamBroadcastHook(event_stream_broadcaster),
            ]

    return EventService(
        event_repo=stack.event_repo,
        hash_service=stack.hash_service,
        subject_repo=stack.subject_repo,
        db=db,
        schema_validator=stack.schema_validator,
        transition_validator=stack.transition_validator,
        subject_type_repo=stack.subject_type_repo,
        post_create_hooks=post_create_hooks,
        epoch_service=stack.epoch_service,
    )


async def get_event_service_for_create(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> EventService:
    """Build EventService for single-event create with retry semantics.

    Uses get_db (no outer transaction) so each retry in create_event runs in
    a fresh transaction (session.begin()), not a savepoint.
    """
    stack = _build_event_service_stack(db, tenant_id, audit_svc)
    # Mutable cell to break circular init: EventService needs engine, engine needs EventService.
    workflow_engine_holder: list[WorkflowEngine | None] = [None]

    def get_workflow_engine() -> WorkflowEngine | None:
        return workflow_engine_holder[0]

    workflow_repo = WorkflowRepository(db, audit_service=audit_svc)
    webhook_repo = WebhookSubscriptionRepository(db)
    oauth_http_client = getattr(request.app.state, "oauth_http_client", None)
    webhook_dispatcher = WebhookDispatcher(
        webhook_repo.get_active_by_tenant,
        http_client=oauth_http_client,
    )
    event_stream_broadcaster = getattr(
        request.app.state, "event_stream_broadcaster", None
    )
    pending_webhook_tasks = getattr(
        request.app.state, "pending_webhook_tasks", None
    )
    event_service = EventService(
        event_repo=stack.event_repo,
        hash_service=stack.hash_service,
        subject_repo=stack.subject_repo,
        db=db,
        schema_validator=stack.schema_validator,
        transition_validator=stack.transition_validator,
        subject_type_repo=stack.subject_type_repo,
        enrichers=DEFAULT_API_ENRICHERS,
        post_create_hooks=[
            WorkflowTriggerHook(get_workflow_engine),
            WebhookDispatchHook(webhook_dispatcher, pending_webhook_tasks),
            EventStreamBroadcastHook(event_stream_broadcaster),
        ],
        epoch_service=stack.epoch_service,
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
    """Callable that runs tenant verification with a fresh session (for background jobs)."""
    async def run_verification_for_tenant(tenant_id: str) -> ChainVerificationResult:
        async with aclosing(get_db()) as gen:
            session = None
            async for session in gen:
                break
            if session is None:
                raise RuntimeError("Failed to obtain database session")
            event_repo = EventRepository(session)
            settings = get_settings()
            svc = VerificationService(
                event_repo=event_repo,
                hash_service=HashService(),
                max_events=settings.verification_max_events,
                timeout_seconds=settings.verification_timeout_seconds,
            )
            return await svc.verify_tenant_chains(tenant_id=tenant_id)

    return run_verification_for_tenant


async def get_event_schema_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventSchemaRepository:
    """Event schema repository for read operations."""
    return EventSchemaRepository(db, cache_service=None, audit_service=None)


async def get_event_schema_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> EventSchemaRepository:
    """Event schema repository for create/update (transactional)."""
    return EventSchemaRepository(db, cache_service=None, audit_service=audit_svc)


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


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

async def get_document_upload_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    tenant_repo: Annotated[TenantRepository, Depends(_core.get_tenant_repo)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> DocumentUploadService:
    """Build DocumentUploadService for upload."""
    storage = _get_storage_from_request(request)
    document_repo = DocumentRepository(db, audit_service=audit_svc)
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)
    category_repo = DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
    metadata_validator = DocumentCategoryMetadataValidator(category_repo)
    return DocumentUploadService(
        storage_service=storage,
        document_repo=document_repo,
        tenant_repo=tenant_repo,
        category_repo=category_repo,
        metadata_validator=metadata_validator,
        subject_repo=subject_repo,
    )


async def get_document_query_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentQueryService:
    """Build DocumentQueryService for metadata, download URL, and listing."""
    storage = _get_storage_from_request(request)
    document_repo = DocumentRepository(db, audit_service=None)
    return DocumentQueryService(
        storage_service=storage,
        document_repo=document_repo,
    )


async def get_document_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRepository:
    """Document repository for read operations."""
    return DocumentRepository(db, audit_service=None)


async def get_document_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> DocumentRepository:
    """Document repository for update/soft-delete."""
    return DocumentRepository(db, audit_service=audit_svc)


async def get_run_document_retention_use_case(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> RunDocumentRetentionUseCase:
    """Run document retention use case (transactional)."""
    document_repo = DocumentRepository(db, audit_service=audit_svc)
    category_repo = DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=None
    )
    return RunDocumentRetentionUseCase(
        document_repo=document_repo,
        document_category_repo=category_repo,
    )


async def get_document_requirement_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRequirementRepository:
    """Document requirement repository for read operations."""
    return DocumentRequirementRepository(db)


async def get_document_requirement_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> DocumentRequirementRepository:
    """Document requirement repository for create/delete."""
    return DocumentRequirementRepository(db)


async def get_document_category_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
) -> DocumentCategoryRepository:
    """Document category repository for read operations (tenant-scoped)."""
    return DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=None
    )


async def get_document_category_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> DocumentCategoryRepository:
    """Document category repository for create/update/delete (transactional)."""
    return DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

async def get_naming_template_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NamingTemplateRepository:
    """Naming template repository for read operations."""
    return NamingTemplateRepository(db)


async def get_naming_template_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> NamingTemplateRepository:
    """Naming template repository for create/update/delete."""
    return NamingTemplateRepository(db)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

async def get_workflow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRepository:
    """Workflow repository for read operations."""
    return WorkflowRepository(db, audit_service=None)


async def get_workflow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> WorkflowRepository:
    """Workflow repository for create/update/delete (transactional)."""
    return WorkflowRepository(db, audit_service=audit_svc)


async def get_workflow_execution_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionRepository:
    """Workflow execution repository for read."""
    return WorkflowExecutionRepository(db)


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

async def get_subject_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> SubjectService:
    """Subject service for create/update/delete (transactional, tenant-scoped)."""
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)
    subject_type_repo = SubjectTypeRepository(db, audit_service=audit_svc)
    schema_validator = SubjectTypeSchemaValidator(subject_type_repo)
    return SubjectService(
        subject_repo,
        subject_type_repo=subject_type_repo,
        schema_validator=schema_validator,
    )


async def get_subject_read_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
) -> SubjectService:
    """Subject service for get/list (read-only, tenant-scoped)."""
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    subject_type_repo = SubjectTypeRepository(db, audit_service=None)
    schema_validator = SubjectTypeSchemaValidator(subject_type_repo)
    return SubjectService(
        subject_repo,
        subject_type_repo=subject_type_repo,
        schema_validator=schema_validator,
    )


async def get_subject_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> SubjectRepository:
    """Subject repository for update/delete (transactional, tenant-scoped)."""
    return SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)


async def get_subject_export_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
) -> SubjectExportService:
    """Subject export use case (read-only)."""
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    return SubjectExportService(
        subject_repo=subject_repo,
        event_repo=EventRepository(db),
        document_repo=DocumentRepository(db),
    )


async def get_subject_erasure_service(
    subject_repo: Annotated[SubjectRepository, Depends(get_subject_repo_for_write)],
    document_repo: Annotated[
        DocumentRepository, Depends(get_document_repo_for_write)
    ],
) -> SubjectErasureService:
    """Subject erasure use case (anonymize or delete)."""
    return SubjectErasureService(
        subject_repo=subject_repo,
        document_repo=document_repo,
    )


async def get_subject_relationship_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> SubjectRelationshipService:
    """Subject relationship use case (add, remove, list). Same transaction as event service."""
    relationship_repo = SubjectRelationshipRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)
    event_service = build_event_service_for_session(db, tenant_id, audit_svc)
    relationship_kind_repo = RelationshipKindRepository(db)
    return SubjectRelationshipService(
        relationship_repo=relationship_repo,
        subject_repo=subject_repo,
        event_service=event_service,
        relationship_kind_repo=relationship_kind_repo,
    )


async def get_subject_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
) -> SubjectRepository:
    """Subject repository for read operations (tenant-scoped)."""
    return SubjectRepository(db, tenant_id=tenant_id, audit_service=None)


async def get_subject_state_use_case(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
) -> GetSubjectStateUseCase:
    """State derivation use case (read-only: event replay, snapshot when available)."""
    event_repo = EventRepository(db)
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    snapshot_repo = SubjectSnapshotRepository(db)
    return GetSubjectStateUseCase(
        event_repo=event_repo,
        subject_repo=subject_repo,
        snapshot_repo=snapshot_repo,
    )


async def get_create_subject_snapshot_use_case(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
) -> CreateSubjectSnapshotUseCase:
    """Create subject snapshot use case (transactional)."""
    event_repo = EventRepository(db)
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    snapshot_repo = SubjectSnapshotRepository(db)
    state_use_case = GetSubjectStateUseCase(
        event_repo=event_repo,
        subject_repo=subject_repo,
        snapshot_repo=snapshot_repo,
    )
    return CreateSubjectSnapshotUseCase(
        state_use_case=state_use_case,
        snapshot_repo=snapshot_repo,
    )


async def get_run_snapshot_job_use_case(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(_core.get_tenant_id)],
    create_snapshot_use_case: Annotated[
        CreateSubjectSnapshotUseCase, Depends(get_create_subject_snapshot_use_case)
    ],
) -> RunSnapshotJobUseCase:
    """Run snapshot job use case (transactional)."""
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    return RunSnapshotJobUseCase(
        subject_repo=subject_repo,
        create_snapshot_use_case=create_snapshot_use_case,
    )


async def get_subject_type_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectTypeRepository:
    """Subject type repository for read operations."""
    return SubjectTypeRepository(db, audit_service=None)


async def get_relationship_kind_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RelationshipKindRepository:
    """Relationship kind repository for read operations."""
    return RelationshipKindRepository(db)


async def get_relationship_kind_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> RelationshipKindRepository:
    """Relationship kind repository for create/update/delete (transactional)."""
    return RelationshipKindRepository(db)


async def get_subject_type_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(_core.get_system_audit_service)],
) -> SubjectTypeRepository:
    """Subject type repository for create/update/delete (transactional)."""
    return SubjectTypeRepository(db, audit_service=audit_svc)


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

async def get_flow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlowRepository:
    """Flow repository for read operations."""
    return FlowRepository(db)


async def get_flow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> FlowRepository:
    """Flow repository for create/update/delete."""
    return FlowRepository(db)


async def get_create_flow_use_case(
    flow_repo: Annotated[FlowRepository, Depends(get_flow_repo_for_write)],
    naming_template_repo: Annotated[
        NamingTemplateRepository, Depends(get_naming_template_repo)
    ],
) -> CreateFlowUseCase:
    """Create flow use case (naming template validation, subject linking)."""
    return CreateFlowUseCase(
        flow_repo=flow_repo,
        naming_template_repo=naming_template_repo,
    )


async def get_flow_document_compliance_use_case(
    flow_repo: Annotated[FlowRepository, Depends(get_flow_repo)],
    document_requirement_repo: Annotated[
        DocumentRequirementRepository, Depends(get_document_requirement_repo)
    ],
    document_category_repo: Annotated[
        DocumentCategoryRepository, Depends(get_document_category_repo)
    ],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
) -> GetFlowDocumentComplianceUseCase:
    """Flow document compliance use case (required vs present docs)."""
    return GetFlowDocumentComplianceUseCase(
        flow_repo=flow_repo,
        document_requirement_repo=document_requirement_repo,
        document_category_repo=document_category_repo,
        document_repo=document_repo,
    )


# ---------------------------------------------------------------------------
# Chain anchor (RFC 3161 TSA)
# ---------------------------------------------------------------------------

async def get_chain_anchor_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChainAnchorRepository:
    """Chain anchor repository for read operations (list, latest)."""
    return ChainAnchorRepository(db)


# ---------------------------------------------------------------------------
# Webhook subscriptions
# ---------------------------------------------------------------------------

async def get_webhook_subscription_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookSubscriptionRepository:
    """Webhook subscription repository for read operations (list, get)."""
    return WebhookSubscriptionRepository(db)


async def get_webhook_subscription_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> WebhookSubscriptionRepository:
    """Webhook subscription repository for create/update/delete."""
    return WebhookSubscriptionRepository(db)


async def get_webhook_dispatcher(
    webhook_repo: Annotated[
        WebhookSubscriptionRepository, Depends(get_webhook_subscription_repo)
    ],
) -> WebhookDispatcher:
    """Webhook dispatcher for test delivery (uses repo to resolve subscriptions)."""
    return WebhookDispatcher(webhook_repo.get_active_by_tenant)


async def get_projection_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectionRepository:
    """Projection repository for read operations."""
    return ProjectionRepository(db)


async def get_projection_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> ProjectionRepository:
    """Projection repository for create/deactivate/rebuild."""
    return ProjectionRepository(db)


async def get_projection_management_use_case(
    repo: Annotated[ProjectionRepository, Depends(get_projection_repo_for_write)],
) -> ProjectionManagementUseCase:
    """Projection management use case (create, list, deactivate, rebuild)."""
    return ProjectionManagementUseCase(projection_repo=repo)


async def get_query_projection_use_case(
    projection_repo: Annotated[ProjectionRepository, Depends(get_projection_repo)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
) -> QueryProjectionUseCase:
    """Query projection use case (current state, as_of replay, list states)."""
    return QueryProjectionUseCase(
        projection_repo=projection_repo,
        event_repo=event_repo,
        registry=get_registry(),
    )


# ---------------------------------------------------------------------------
# Search / analytics
# ---------------------------------------------------------------------------

async def get_search_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchRepository:
    """Search repository for full-text search (read-only)."""
    return SearchRepository(db)


async def get_search_service(
    search_repo: Annotated[SearchRepository, Depends(get_search_repo)],
) -> SearchService:
    """Search use case (full-text across subjects, events, documents)."""
    return SearchService(search_repo)


async def get_dashboard_stats_use_case(
    subject_repo: Annotated[SubjectRepository, Depends(get_subject_repo)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
) -> GetDashboardStatsUseCase:
    """Dashboard stats use case (counts and recent activity)."""
    return GetDashboardStatsUseCase(
        subject_repo=subject_repo,
        event_repo=event_repo,
        document_repo=document_repo,
    )
