"""Presentation-layer dependency injection (composition root).

Provides FastAPI Depends() for DB sessions and application use cases.
All use cases are built from infrastructure implementations here;
routes depend only on these dependencies, not on infra directly.

Repositories use SQLAlchemy and PostgreSQL only.
"""

from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserResult
from app.application.services.authorization_service import AuthorizationService
from app.application.services.event_schema_validator import EventSchemaValidator
from app.application.services.event_transition_validator import EventTransitionValidator
from app.application.services.hash_service import HashService
from app.application.services.document_category_metadata_validator import (
    DocumentCategoryMetadataValidator,
)
from app.application.services.subject_type_schema_validator import (
    SubjectTypeSchemaValidator,
)
from app.application.services.permission_service import PermissionService
from app.application.services.role_service import RoleService
from app.application.services.tenant_creation_service import TenantCreationService
from app.application.services.user_service import UserService
from app.application.services.verification_service import (
    ChainVerificationResult,
    VerificationService,
)
from app.application.use_cases.documents import (
    DocumentQueryService,
    DocumentUploadService,
    RunDocumentRetentionUseCase,
)
from app.application.use_cases.analytics import GetDashboardStatsUseCase
from app.application.use_cases.events import EventService
from app.application.use_cases.search import SearchService
from app.application.use_cases.flows import (
    CreateFlowUseCase,
    GetFlowDocumentComplianceUseCase,
)
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
from app.core.tenant_validation import is_valid_tenant_id_format
from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import (
    EnvelopeEncryptor,
    OAuthStateManager,
)
from app.infrastructure.external.email.oauth_drivers import OAuthDriverRegistry
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.password import get_password_hash
from app.infrastructure.persistence.database import (
    get_db,
    get_db_transactional,
)
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.repositories import (
    AuditLogRepository,
    DocumentCategoryRepository,
    DocumentRepository,
    DocumentRequirementRepository,
    EmailAccountRepository,
    EventRepository,
    EventSchemaRepository,
    EventTransitionRuleRepository,
    FlowRepository,
    NamingTemplateRepository,
    OAuthProviderConfigRepository,
    OAuthStateRepository,
    PasswordSetTokenStore,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    SearchRepository,
    RelationshipKindRepository,
    SubjectRelationshipRepository,
    SubjectRepository,
    SubjectSnapshotRepository,
    SubjectTypeRepository,
    TenantRepository,
    UserRepository,
    UserRoleRepository,
    WorkflowExecutionRepository,
    WorkflowRepository,
    TaskRepository,
)
from app.infrastructure.services.workflow_notification_service import (
    LogOnlyNotificationService,
    WorkflowRecipientResolver,
)
from app.infrastructure.services.workflow_template_renderer import WorkflowTemplateRenderer
from app.infrastructure.services import (
    PermissionResolver,
    SystemAuditService,
    TenantInitializationService,
    WorkflowEngine,
)
from app.infrastructure.services.email_account_service import EmailAccountService
from app.infrastructure.services.api_audit_log_service import ApiAuditLogService
from app.infrastructure.services.oauth_config_service import OAuthConfigService
from app.shared.request_audit import (
    get_audit_action_from_method,
    get_audit_request_context,
    get_audit_resource_from_path,
    get_tenant_and_user_for_audit,
)

# Short TTL for tenant-ID validation cache (reduce DB load; avoid long-lived negative cache).
_TENANT_VALIDATION_CACHE_TTL = 60
_TENANT_CACHE_MISS_MARKER = "__missing__"


class AuthSecurity:
    """Token and password hashing provided via DI (no direct infra imports in routes)."""

    def create_access_token(self, data: dict) -> str:
        return create_access_token(data)

    def hash_password(self, password: str) -> str:
        return get_password_hash(password)


def get_auth_security() -> AuthSecurity:
    """Auth token creation and password hashing (composition root)."""
    return AuthSecurity()


def get_credential_encryptor() -> CredentialEncryptor:
    """Credential encryptor for email accounts (composition root)."""
    return CredentialEncryptor()


def get_envelope_encryptor() -> EnvelopeEncryptor:
    """Envelope encryptor for OAuth client secrets (composition root)."""
    return EnvelopeEncryptor()


def get_oauth_state_manager() -> OAuthStateManager:
    """OAuth state signing/verification (composition root)."""
    return OAuthStateManager()


def get_oauth_driver_registry(request: Request) -> OAuthDriverRegistry:
    """OAuth driver registry with shared HTTP client (composition root)."""
    http_client = getattr(request.app.state, "oauth_http_client", None)
    return OAuthDriverRegistry(http_client=http_client)


async def get_system_audit_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SystemAuditService:
    """Build SystemAuditService for Postgres write path (same session as request)."""
    return SystemAuditService(db, HashService())


async def get_set_password_deps(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> tuple[PasswordSetTokenStore, UserRepository]:
    """Token store and user repo for POST /auth/set-initial-password (same transaction). Postgres only."""
    audit_svc = SystemAuditService(db, HashService())
    return (PasswordSetTokenStore(db), UserRepository(db, audit_service=audit_svc))


async def get_tenant_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantRepository:
    """Tenant repository for read operations."""
    return TenantRepository(db, cache_service=None, audit_service=None)


async def get_tenant_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> TenantRepository:
    """Tenant repository for writes (transactional)."""
    audit_svc = SystemAuditService(db, HashService())
    return TenantRepository(db, cache_service=None, audit_service=audit_svc)


async def get_tenant_id(
    request: Request,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repo)],
) -> str:
    """Resolve tenant ID from header and validate it exists.

    Uses app.state.cache (short TTL) when available to avoid hitting the tenant
    repository on every request.
    """
    name = get_settings().tenant_header_name
    value = request.headers.get(name)
    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {name}",
        )
    if not is_valid_tenant_id_format(value):
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant ID format (use alphanumeric, hyphen, underscore; max 64 characters)",
        )
    cache = getattr(request.app.state, "cache", None)
    cache_key = f"tenant:{value}"
    if cache and cache.is_available():
        cached = await cache.get(cache_key)
        if cached is not None:
            if cached == _TENANT_CACHE_MISS_MARKER:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or unknown tenant",
                )
            return value
    tenant = await tenant_repo.get_by_id(value)
    if not tenant:
        if cache and cache.is_available():
            await cache.set(
                cache_key, _TENANT_CACHE_MISS_MARKER, ttl=_TENANT_VALIDATION_CACHE_TTL
            )
        raise HTTPException(
            status_code=400,
            detail="Invalid or unknown tenant",
        )
    if cache and cache.is_available():
        await cache.set(cache_key, value, ttl=_TENANT_VALIDATION_CACHE_TTL)
    return value


def get_verified_tenant_id(
    tenant_id: str,
    tenant_id_header: Annotated[str, Depends(get_tenant_id)],
) -> str:
    """Ensure path tenant_id matches X-Tenant-ID header; return tenant_id or raise 403."""
    if tenant_id != tenant_id_header:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tenant_id


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
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> EventService:
    """Build EventService with hash chaining, schema validation, and workflow engine.

    EventService and WorkflowEngine depend on each other (event creation can trigger
    workflows; workflows can create events). We break the cycle by:
    1. Creating EventService with a provider that returns the engine from a holder.
    2. Creating WorkflowEngine with the event service.
    3. Storing the engine in the holder so the provider resolves on first use.
    """
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


async def get_document_upload_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repo)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> DocumentUploadService:
    """Build DocumentUploadService for upload (storage + document/tenant repos + optional category metadata validation).

    Reuses the same TenantRepository instance as get_tenant_id to avoid a second
    tenant lookup in the same request.
    """
    storage = StorageFactory.create_storage_service()
    document_repo = DocumentRepository(db, audit_service=audit_svc)
    subject_repo = SubjectRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentQueryService:
    """Build DocumentQueryService for metadata, download URL, and listing."""
    storage = StorageFactory.create_storage_service()
    document_repo = DocumentRepository(db)
    return DocumentQueryService(
        storage_service=storage,
        document_repo=document_repo,
    )


async def get_document_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRepository:
    """Document repository for read operations (list by event, get versions)."""
    return DocumentRepository(db, audit_service=None)


async def get_document_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> DocumentRepository:
    """Document repository for update/soft-delete."""
    return DocumentRepository(db, audit_service=audit_svc)


async def get_run_document_retention_use_case(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> RunDocumentRetentionUseCase:
    """Run document retention use case (transactional: category-based soft-delete)."""
    document_repo = DocumentRepository(db, audit_service=audit_svc)
    category_repo = DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=None
    )
    return RunDocumentRetentionUseCase(
        document_repo=document_repo,
        document_category_repo=category_repo,
    )


async def get_tenant_creation_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> TenantCreationService:
    """Build TenantCreationService (Postgres)."""
    audit_svc = SystemAuditService(db, HashService())
    token_store = PasswordSetTokenStore(db)
    return TenantCreationService(
        tenant_repo=TenantRepository(db),
        user_repo=UserRepository(db, audit_service=audit_svc),
        init_service=TenantInitializationService(db),
        audit_service=audit_svc,
        token_store=token_store,
    )


async def get_authorization_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthorizationService:
    """Build AuthorizationService with permission resolver and optional cache.

    Cache is set in app lifespan (app.state.cache) when Redis is enabled;
    otherwise cache is None and permission checks hit the DB only.
    """
    settings = get_settings()
    permission_resolver = PermissionResolver(db)
    cache = getattr(request.app.state, "cache", None)
    return AuthorizationService(
        permission_resolver=permission_resolver,
        cache=cache,
        cache_ttl=settings.cache_ttl_permissions,
    )


# ---- Read-only repo / service dependencies (get_db for reads) ----


async def get_event_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventRepository:
    """Event repository for read operations (list, get by id)."""
    return EventRepository(db)


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


async def get_subject_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> SubjectService:
    """Subject service for create/get/list (transactional, tenant-scoped)."""
    subject_repo = SubjectRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
    subject_type_repo = SubjectTypeRepository(db, audit_service=audit_svc)
    schema_validator = SubjectTypeSchemaValidator(subject_type_repo)
    return SubjectService(
        subject_repo,
        subject_type_repo=subject_type_repo,
        schema_validator=schema_validator,
    )


async def get_subject_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> SubjectRepository:
    """Subject repository for update/delete (transactional, tenant-scoped)."""
    return SubjectRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )


async def get_subject_export_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> SubjectExportService:
    """Subject export use case (read-only: subject + events + document refs)."""
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    return SubjectExportService(
        subject_repo=subject_repo,
        event_repo=EventRepository(db),
        document_repo=DocumentRepository(db),
    )


async def get_subject_erasure_service(
    subject_repo: Annotated[SubjectRepository, Depends(get_subject_repo_for_write)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo_for_write)],
) -> SubjectErasureService:
    """Subject erasure use case (anonymize or delete)."""
    return SubjectErasureService(
        subject_repo=subject_repo,
        document_repo=document_repo,
    )


async def get_subject_relationship_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> SubjectRelationshipService:
    """Subject relationship use case (add, remove, list). Tenant-scoped.

    Uses same DB session as event service so relationship + timeline events
    are in one transaction.
    """
    relationship_repo = SubjectRelationshipRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
    subject_repo = SubjectRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
    event_service = _build_event_service_for_session(db, tenant_id, audit_svc)
    relationship_kind_repo = RelationshipKindRepository(db)
    return SubjectRelationshipService(
        relationship_repo=relationship_repo,
        subject_repo=subject_repo,
        event_service=event_service,
        relationship_kind_repo=relationship_kind_repo,
    )


async def get_subject_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> SubjectRepository:
    """Subject repository for read operations (tenant-scoped, no audit)."""
    return SubjectRepository(db, tenant_id=tenant_id, audit_service=None)


async def get_get_subject_state_use_case(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> GetSubjectStateUseCase:
    """State derivation use case (read-only: event replay; uses snapshot when available)."""
    event_repo = EventRepository(db)
    subject_repo = SubjectRepository(
        db, tenant_id=tenant_id, audit_service=None
    )
    snapshot_repo = SubjectSnapshotRepository(db)
    return GetSubjectStateUseCase(
        event_repo=event_repo,
        subject_repo=subject_repo,
        snapshot_repo=snapshot_repo,
    )


async def get_create_subject_snapshot_use_case(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> CreateSubjectSnapshotUseCase:
    """Create subject snapshot use case (transactional: read state then write snapshot)."""
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
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    create_snapshot_use_case: Annotated[
        CreateSubjectSnapshotUseCase, Depends(get_create_subject_snapshot_use_case)
    ],
) -> RunSnapshotJobUseCase:
    """Run snapshot job use case (transactional: list subjects then create snapshots)."""
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=None)
    return RunSnapshotJobUseCase(
        subject_repo=subject_repo,
        create_snapshot_use_case=create_snapshot_use_case,
    )


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


async def get_event_schema_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventSchemaRepository:
    """Event schema repository for read operations."""
    return EventSchemaRepository(db, cache_service=None, audit_service=None)


async def get_event_schema_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> SubjectTypeRepository:
    """Subject type repository for create/update/delete (transactional)."""
    return SubjectTypeRepository(db, audit_service=audit_svc)


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
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> DocumentCategoryRepository:
    """Document category repository for read operations (tenant-scoped)."""
    return DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=None
    )


async def get_document_category_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> DocumentCategoryRepository:
    """Document category repository for create/update/delete (transactional, tenant-scoped)."""
    return DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )


async def get_user_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    """User repository for read operations."""
    return UserRepository(db, audit_service=None)


async def get_user_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> UserRepository:
    """User repository for writes (transactional)."""
    audit_svc = SystemAuditService(db, HashService())
    return UserRepository(db, audit_service=audit_svc)


async def get_workflow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRepository:
    """Workflow repository for read operations (list, get by id)."""
    return WorkflowRepository(db, audit_service=None)


async def get_workflow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> WorkflowRepository:
    """Workflow repository for create/update/delete (transactional)."""
    audit_svc = SystemAuditService(db, HashService())
    return WorkflowRepository(db, audit_service=audit_svc)


async def get_workflow_execution_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionRepository:
    """Workflow execution repository for read (list by workflow, get by id)."""
    return WorkflowExecutionRepository(db)


async def get_flow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlowRepository:
    """Flow repository for read operations. Requires PostgreSQL."""
    return FlowRepository(db)


async def get_flow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> FlowRepository:
    """Flow repository for create/update/delete. Requires PostgreSQL."""
    return FlowRepository(db)


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


async def get_role_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleRepository:
    """Role repository for read operations (list, get by id)."""
    return RoleRepository(db, audit_service=None)


async def get_role_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> RoleRepository:
    """Role repository for create/update/delete."""
    return RoleRepository(db, audit_service=audit_svc)


async def get_permission_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionRepository:
    """Permission repository for read operations and user/role assignment."""
    return PermissionRepository(db, audit_service=None)


async def get_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> PermissionRepository:
    """Permission repository for create/update/delete (transactional)."""
    return PermissionRepository(db, audit_service=audit_svc)


async def get_role_permission_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RolePermissionRepository:
    """Role-permission repository for read (e.g. get_permissions_for_role)."""
    return RolePermissionRepository(db, audit_service=None)


async def get_role_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> RolePermissionRepository:
    """Role-permission repository for assign/remove (transactional)."""
    return RolePermissionRepository(db, audit_service=audit_svc)


async def get_user_role_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRoleRepository:
    """User-role repository for read (e.g. get_user_roles)."""
    return UserRoleRepository(db, audit_service=None)


async def get_user_role_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> UserRoleRepository:
    """User-role repository for assign/remove (transactional)."""
    return UserRoleRepository(db, audit_service=audit_svc)


async def get_audit_log_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogRepository:
    """Audit log repository for read (list). Writes are via ensure_audit_logged (same transaction)."""
    return AuditLogRepository(db)


async def ensure_audit_logged(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> AsyncIterator[None]:
    """Dependency that writes API audit log in the same transaction when the route returns normally.

    Add to write endpoints (POST/PUT/PATCH/DELETE) so the audit row is committed
    in the same transaction as the mutation. If the route raises, the transaction
    rolls back and no audit row is written.
    """
    yield
    # After route returned normally: write audit in same transaction before commit.
    tenant_id, user_id = get_tenant_and_user_for_audit(request)
    if not tenant_id:
        return
    resource_type, resource_id = get_audit_resource_from_path(request.url.path)
    if not resource_type:
        return
    request_id, ip_address, user_agent = get_audit_request_context(request)
    action = get_audit_action_from_method(request.method)
    try:
        svc = ApiAuditLogService(db)
        await svc.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=None,
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
            error_message=None,
        )
    except Exception:
        # Let the transaction roll back by re-raising; dependency cleanup will see it.
        raise


async def get_oauth_provider_config_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for read operations."""
    return OAuthProviderConfigRepository(db, audit_service=None)


async def get_oauth_provider_config_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for create/update/delete (transactional)."""
    return OAuthProviderConfigRepository(db, audit_service=audit_svc)


async def get_oauth_state_repo(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
) -> OAuthStateRepository:
    """OAuth state repository for authorize/callback (transactional)."""
    return OAuthStateRepository(db, state_manager=state_manager)


async def get_email_account_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailAccountRepository:
    """Email account repository for read operations (list, get by id)."""
    return EmailAccountRepository(db)


async def get_email_account_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EmailAccountRepository:
    """Email account repository for create/update/delete (transactional)."""
    return EmailAccountRepository(db)


async def get_oauth_config_service(
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    state_repo: Annotated[
        OAuthStateRepository, Depends(get_oauth_state_repo)
    ],
    envelope_encryptor: Annotated[EnvelopeEncryptor, Depends(get_envelope_encryptor)],
    driver_registry: Annotated[OAuthDriverRegistry, Depends(get_oauth_driver_registry)],
) -> OAuthConfigService:
    """OAuth config and flow service (composition root)."""
    return OAuthConfigService(
        oauth_repo=oauth_repo,
        state_repo=state_repo,
        envelope_encryptor=envelope_encryptor,
        driver_registry=driver_registry,
    )


def get_email_account_service(
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    credential_encryptor: CredentialEncryptor = Depends(get_credential_encryptor),
) -> EmailAccountService:
    """Email account service (composition root)."""
    return EmailAccountService(
        email_account_repo=email_account_repo,
        credential_encryptor=credential_encryptor,
    )


def get_role_service(
    role_repo: Annotated[RoleRepository, Depends(get_role_repo_for_write)],
    permission_repo: Annotated[PermissionRepository, Depends(get_permission_repo)],
    role_permission_repo: Annotated[
        RolePermissionRepository, Depends(get_role_permission_repo_for_write)
    ],
) -> RoleService:
    """Role service for create-with-permissions (composition root)."""
    return RoleService(
        role_repo=role_repo,
        permission_repo=permission_repo,
        role_permission_repo=role_permission_repo,
    )


def get_permission_service(
    permission_repo: Annotated[
        PermissionRepository, Depends(get_permission_repo_for_write)
    ],
) -> PermissionService:
    """Permission service (composition root)."""
    return PermissionService(permission_repo=permission_repo)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo_for_write)],
    auth_security: AuthSecurity = Depends(get_auth_security),
) -> UserService:
    """User service for update-me (composition root)."""
    return UserService(user_repo=user_repo, auth_security=auth_security)


# ---- Auth (current user from JWT) ----

_http_bearer = HTTPBearer(auto_error=False)


def _to_user_result(user: User | UserResult) -> UserResult:
    """Normalize repo result (ORM User or UserResult) to UserResult for consistent typing."""
    if isinstance(user, UserResult):
        return user
    return UserResult(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
    )


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserResult | None:
    """Return current user from JWT if present; else None. Use for optional auth routes."""
    if not credentials:
        return None
    try:
        from app.infrastructure.security.jwt import verify_token

        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            return None
        user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
        if not user or not user.is_active:
            return None
        return _to_user_result(user)
    except (ValueError, KeyError):
        return None


async def get_current_user(
    current_user: Annotated[UserResult | None, Depends(get_current_user_optional)],
) -> UserResult:
    """Return current user from JWT; raise 401 if missing or invalid."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


def require_permission(resource: str, action: str):
    """Dependency factory: require JWT auth and that the user has resource:action."""

    async def _require(
        current_user: Annotated[UserResult, Depends(get_current_user)],
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> UserResult:
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        await auth_svc.require_permission(
            current_user.id, tenant_id, resource, action
        )
        return current_user

    return _require
