"""Presentation-layer dependency injection (composition root).

Provides FastAPI Depends() for DB sessions and application use cases.
All use cases are built from infrastructure implementations here;
routes depend only on these dependencies, not on infra directly.

When database_backend is 'postgres', repositories use SQLAlchemy.
When database_backend is 'firestore', tenant/user/tenant-creation use Firestore.
Switch backends via DATABASE_BACKEND in config.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserResult
from app.application.services.authorization_service import AuthorizationService
from app.application.services.event_schema_validator import EventSchemaValidator
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
from app.application.services.verification_service import VerificationService
from app.application.use_cases.documents import (
    DocumentQueryService,
    DocumentUploadService,
)
from app.application.use_cases.analytics import GetDashboardStatsUseCase
from app.application.use_cases.events import EventService
from app.application.use_cases.search import SearchService
from app.application.use_cases.state import GetSubjectStateUseCase
from app.application.use_cases.subjects import (
    SubjectErasureService,
    SubjectExportService,
    SubjectService,
)
from app.core.config import get_settings
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
    EmailAccountRepository,
    EventRepository,
    EventSchemaRepository,
    OAuthProviderConfigRepository,
    OAuthStateRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    SearchRepository,
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
from app.infrastructure.services.oauth_config_service import OAuthConfigService

# Firestore-backed repos and services (used when database_backend == "firestore")
from app.infrastructure.firebase._rest_client import FirestoreRESTClient
from app.infrastructure.firebase.client import get_firestore_client
from app.infrastructure.firebase.repositories import (
    FirestoreTenantRepository,
    FirestoreUserRepository,
)
from app.infrastructure.firebase.services import FirestoreTenantInitializationService

# Short TTL for tenant-ID validation cache (reduce DB load; avoid long-lived negative cache).
_TENANT_VALIDATION_CACHE_TTL = 60
_TENANT_CACHE_MISS_MARKER = "__missing__"


@dataclass
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


@dataclass
class DbOrFirestore:
    """Either a Postgres session or a Firestore client for swappable backends."""

    db: AsyncSession | None
    firestore: FirestoreRESTClient | None


def _get_firestore_client_or_raise() -> FirestoreRESTClient:
    """Return Firestore client or raise HTTPException 503 with standard message."""
    client = get_firestore_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Firestore not configured (set FIREBASE_SERVICE_ACCOUNT_KEY or PATH)",
        )
    return client


async def _get_db_or_firestore_read() -> AsyncGenerator[DbOrFirestore, None]:
    """Yield DB session (read) or Firestore client based on config."""
    settings = get_settings()
    if settings.database_backend == "postgres":
        async for session in get_db():
            yield DbOrFirestore(db=session, firestore=None)
    else:
        client = _get_firestore_client_or_raise()
        yield DbOrFirestore(db=None, firestore=client)


async def _get_db_or_firestore_write() -> AsyncGenerator[DbOrFirestore, None]:
    """Yield DB session (transactional) or Firestore client based on config."""
    settings = get_settings()
    if settings.database_backend == "postgres":
        async for session in get_db_transactional():
            yield DbOrFirestore(db=session, firestore=None)
    else:
        client = _get_firestore_client_or_raise()
        yield DbOrFirestore(db=None, firestore=client)


async def get_system_audit_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SystemAuditService:
    """Build SystemAuditService for Postgres write path (same session as request)."""
    return SystemAuditService(db, HashService())


async def get_tenant_repo(
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_read)],
) -> TenantRepository | FirestoreTenantRepository:
    """Tenant repository (Postgres or Firestore from config)."""
    if backend.db is not None:
        return TenantRepository(backend.db, cache_service=None, audit_service=None)
    assert backend.firestore is not None
    return FirestoreTenantRepository(backend.firestore)


async def get_tenant_repo_for_write(
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_write)],
) -> TenantRepository | FirestoreTenantRepository:
    """Tenant repository for writes (Postgres or Firestore from config)."""
    if backend.db is not None:
        audit_svc = SystemAuditService(backend.db, HashService())
        return TenantRepository(
            backend.db, cache_service=None, audit_service=audit_svc
        )
    assert backend.firestore is not None
    return FirestoreTenantRepository(backend.firestore)


async def get_tenant_id(
    request: Request,
    tenant_repo: Annotated[
        TenantRepository | FirestoreTenantRepository,
        Depends(get_tenant_repo),
    ],
) -> str:
    """Resolve tenant ID from header and validate it exists (Postgres or Firestore).

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


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> EventService:
    """Build EventService with hash chaining, schema validation, and workflow engine.

    EventService and WorkflowEngine depend on each other (event creation can trigger
    workflows; workflows can create events). We break the cycle by:
    1. Creating EventService with a provider that returns the engine from a holder.
    2. Creating WorkflowEngine with the event service.
    3. Storing the engine in the holder so the provider resolves on first use.
    """
    event_repo = EventRepository(db)
    hash_service = HashService()
    subject_repo = SubjectRepository(db, tenant_id=tenant_id, audit_service=audit_svc)
    schema_repo = EventSchemaRepository(
        db, cache_service=None, audit_service=audit_svc
    )
    schema_validator = EventSchemaValidator(schema_repo)
    workflow_repo = WorkflowRepository(db, audit_service=audit_svc)

    workflow_engine_holder: list[WorkflowEngine | None] = [None]

    def get_workflow_engine() -> WorkflowEngine | None:
        return workflow_engine_holder[0]

    event_service = EventService(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_validator=schema_validator,
        workflow_engine_provider=get_workflow_engine,
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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> DocumentUploadService:
    """Build DocumentUploadService for upload (storage + document/tenant repos + optional category metadata validation)."""
    storage = StorageFactory.create_storage_service()
    document_repo = DocumentRepository(db, audit_service=audit_svc)
    tenant_repo = TenantRepository(db)
    category_repo = DocumentCategoryRepository(db, audit_service=audit_svc)
    metadata_validator = DocumentCategoryMetadataValidator(category_repo)
    return DocumentUploadService(
        storage_service=storage,
        document_repo=document_repo,
        tenant_repo=tenant_repo,
        category_repo=category_repo,
        metadata_validator=metadata_validator,
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


async def get_tenant_creation_service(
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_write)],
) -> TenantCreationService:
    """Build TenantCreationService (Postgres or Firestore from config)."""
    if backend.db is not None:
        audit_svc = SystemAuditService(backend.db, HashService())
        return TenantCreationService(
            tenant_repo=TenantRepository(backend.db),
            user_repo=UserRepository(backend.db, audit_service=audit_svc),
            init_service=TenantInitializationService(backend.db),
            audit_service=audit_svc,
        )
    assert backend.firestore is not None
    return TenantCreationService(
        tenant_repo=FirestoreTenantRepository(backend.firestore),
        user_repo=FirestoreUserRepository(backend.firestore),
        init_service=FirestoreTenantInitializationService(backend.firestore),
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


async def get_subject_type_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectTypeRepository:
    """Subject type repository for read operations."""
    return SubjectTypeRepository(db, audit_service=None)


async def get_subject_type_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> SubjectTypeRepository:
    """Subject type repository for create/update/delete (transactional)."""
    return SubjectTypeRepository(db, audit_service=audit_svc)


async def get_document_category_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentCategoryRepository:
    """Document category repository for read operations."""
    return DocumentCategoryRepository(db, audit_service=None)


async def get_document_category_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> DocumentCategoryRepository:
    """Document category repository for create/update/delete (transactional)."""
    return DocumentCategoryRepository(db, audit_service=audit_svc)


async def get_user_repo(
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_read)],
) -> UserRepository | FirestoreUserRepository:
    """User repository (Postgres or Firestore from config)."""
    if backend.db is not None:
        return UserRepository(backend.db, audit_service=None)
    assert backend.firestore is not None
    return FirestoreUserRepository(backend.firestore)


async def get_user_repo_for_write(
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_write)],
) -> UserRepository | FirestoreUserRepository:
    """User repository for writes (Postgres or Firestore from config)."""
    if backend.db is not None:
        audit_svc = SystemAuditService(backend.db, HashService())
        return UserRepository(backend.db, audit_service=audit_svc)
    assert backend.firestore is not None
    return FirestoreUserRepository(backend.firestore)


async def get_workflow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRepository:
    """Workflow repository for read operations (list, get by id)."""
    return WorkflowRepository(db, audit_service=None)


async def get_workflow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> WorkflowRepository:
    """Workflow repository for create/update/delete (transactional)."""
    return WorkflowRepository(db, audit_service=audit_svc)


async def get_workflow_execution_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionRepository:
    """Workflow execution repository for read (list by workflow, get by id)."""
    return WorkflowExecutionRepository(db)


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
    """Role–permission repository for read (e.g. get_permissions_for_role)."""
    return RolePermissionRepository(db, audit_service=None)


async def get_role_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> RolePermissionRepository:
    """Role–permission repository for assign/remove (transactional)."""
    return RolePermissionRepository(db, audit_service=audit_svc)


async def get_user_role_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRoleRepository:
    """User–role repository for read (e.g. get_user_roles)."""
    return UserRoleRepository(db, audit_service=None)


async def get_user_role_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> UserRoleRepository:
    """User–role repository for assign/remove (transactional)."""
    return UserRoleRepository(db, audit_service=audit_svc)


async def get_audit_log_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogRepository:
    """Audit log repository for read (list). Writes are via ApiAuditLogService in middleware."""
    return AuditLogRepository(db)


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
    request: Request,
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    state_repo: Annotated[
        OAuthStateRepository, Depends(get_oauth_state_repo)
    ],
    envelope_encryptor: EnvelopeEncryptor = Depends(get_envelope_encryptor),
    driver_registry: OAuthDriverRegistry = Depends(get_oauth_driver_registry),
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
