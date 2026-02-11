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

from app.application.services.authorization_service import AuthorizationService
from app.application.services.event_schema_validator import EventSchemaValidator
from app.application.services.hash_service import HashService
from app.application.services.tenant_creation_service import TenantCreationService
from app.application.services.verification_service import VerificationService
from app.application.use_cases.documents import (
    DocumentQueryService,
    DocumentUploadService,
)
from app.application.use_cases.events import EventService
from app.application.use_cases.subjects import SubjectService
from app.core.config import get_settings
from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import EnvelopeEncryptor
from app.infrastructure.external.email.oauth_drivers import OAuthDriverRegistry
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.password import get_password_hash
from app.infrastructure.persistence.database import (
    AsyncSessionLocal,
    get_db,
    get_db_transactional,
    _ensure_engine,
)
from app.infrastructure.persistence.repositories import (
    DocumentRepository,
    EmailAccountRepository,
    EventRepository,
    EventSchemaRepository,
    OAuthProviderConfigRepository,
    OAuthStateRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    SubjectRepository,
    TenantRepository,
    UserRepository,
    UserRoleRepository,
    WorkflowExecutionRepository,
    WorkflowRepository,
)
from app.infrastructure.services import (
    PermissionResolver,
    TenantInitializationService,
    WorkflowEngine,
)

# Firestore-backed repos and services (used when database_backend == "firestore")
from app.infrastructure.firebase._rest_client import FirestoreRESTClient
from app.infrastructure.firebase.client import get_firestore_client
from app.infrastructure.firebase.repositories import (
    FirestoreTenantRepository,
    FirestoreUserRepository,
)
from app.infrastructure.firebase.services import FirestoreTenantInitializationService


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


def get_oauth_driver_registry() -> OAuthDriverRegistry:
    """OAuth driver registry (composition root)."""
    return OAuthDriverRegistry()


@dataclass
class DbOrFirestore:
    """Either a Postgres session or a Firestore client for swappable backends."""

    db: AsyncSession | None
    firestore: FirestoreRESTClient | None


async def _get_db_or_firestore_read() -> AsyncGenerator[DbOrFirestore, None]:
    """Yield DB session (read) or Firestore client based on config."""
    settings = get_settings()
    if settings.database_backend == "postgres":
        _ensure_engine()
        if AsyncSessionLocal is None:
            raise HTTPException(
                status_code=503,
                detail="Postgres not configured (set DATABASE_BACKEND=postgres and DATABASE_URL)",
            )
        async with AsyncSessionLocal() as session:
            yield DbOrFirestore(db=session, firestore=None)
    else:
        client = get_firestore_client()
        if not client:
            raise HTTPException(
                status_code=503,
                detail="Firestore not configured (set FIREBASE_SERVICE_ACCOUNT_KEY or PATH)",
            )
        yield DbOrFirestore(db=None, firestore=client)


async def _get_db_or_firestore_write() -> AsyncGenerator[DbOrFirestore, None]:
    """Yield DB session (transactional) or Firestore client based on config."""
    settings = get_settings()
    if settings.database_backend == "postgres":
        _ensure_engine()
        if AsyncSessionLocal is None:
            raise HTTPException(
                status_code=503,
                detail="Postgres not configured (set DATABASE_BACKEND=postgres and DATABASE_URL)",
            )
        async with AsyncSessionLocal() as session:
            async with session.begin():
                yield DbOrFirestore(db=session, firestore=None)
    else:
        client = get_firestore_client()
        if not client:
            raise HTTPException(
                status_code=503,
                detail="Firestore not configured (set FIREBASE_SERVICE_ACCOUNT_KEY or PATH)",
            )
        yield DbOrFirestore(db=None, firestore=client)


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
        return TenantRepository(backend.db, cache_service=None, audit_service=None)
    assert backend.firestore is not None
    return FirestoreTenantRepository(backend.firestore)


async def get_tenant_id(
    request: Request,
    tenant_repo: Annotated[
        TenantRepository | FirestoreTenantRepository,
        Depends(get_tenant_repo),
    ],
) -> str:
    """Resolve tenant ID from header and validate it exists (Postgres or Firestore)."""
    name = get_settings().tenant_header_name
    value = request.headers.get(name)
    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {name}",
        )
    tenant = await tenant_repo.get_by_id(value)
    if not tenant:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unknown tenant",
        )
    return value


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EventService:
    """Build EventService with hash chaining, schema validation, and workflow engine."""
    event_repo = EventRepository(db)
    hash_service = HashService()
    subject_repo = SubjectRepository(db, audit_service=None)
    schema_repo = EventSchemaRepository(db, cache_service=None, audit_service=None)
    schema_validator = EventSchemaValidator(schema_repo)
    workflow_repo = WorkflowRepository(db, audit_service=None)
    event_service = EventService(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_validator=schema_validator,
        workflow_engine_provider=lambda: workflow_engine,
    )
    workflow_engine = WorkflowEngine(db, event_service, workflow_repo)
    return event_service


async def get_document_upload_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> DocumentUploadService:
    """Build DocumentUploadService for upload (storage + document/tenant repos)."""
    storage = StorageFactory.create_storage_service()
    document_repo = DocumentRepository(db)
    tenant_repo = TenantRepository(db)
    return DocumentUploadService(
        storage_service=storage,
        document_repo=document_repo,
        tenant_repo=tenant_repo,
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
) -> DocumentRepository:
    """Document repository for update/soft-delete."""
    return DocumentRepository(db, audit_service=None)


async def get_tenant_creation_service(
    backend: Annotated[DbOrFirestore, Depends(_get_db_or_firestore_write)],
) -> TenantCreationService:
    """Build TenantCreationService (Postgres or Firestore from config)."""
    if backend.db is not None:
        return TenantCreationService(
            tenant_repo=TenantRepository(backend.db),
            user_repo=UserRepository(backend.db),
            init_service=TenantInitializationService(backend.db),
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


async def get_verification_service(
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
) -> VerificationService:
    """Verification service for event chain integrity (hash + previous_hash)."""
    return VerificationService(event_repo=event_repo, hash_service=HashService())


async def get_subject_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SubjectService:
    """Subject service for create/get/list (uses transactional session)."""
    subject_repo = SubjectRepository(db, audit_service=None)
    return SubjectService(subject_repo)


async def get_subject_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SubjectRepository:
    """Subject repository for update/delete (transactional)."""
    return SubjectRepository(db, audit_service=None)


async def get_event_schema_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventSchemaRepository:
    """Event schema repository for read operations."""
    return EventSchemaRepository(db, cache_service=None, audit_service=None)


async def get_event_schema_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EventSchemaRepository:
    """Event schema repository for create/update (transactional)."""
    return EventSchemaRepository(db, cache_service=None, audit_service=None)


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
        return UserRepository(backend.db, audit_service=None)
    assert backend.firestore is not None
    return FirestoreUserRepository(backend.firestore)


async def get_workflow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRepository:
    """Workflow repository for read operations (list, get by id)."""
    return WorkflowRepository(db, audit_service=None)


async def get_workflow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> WorkflowRepository:
    """Workflow repository for create/update/delete (transactional)."""
    return WorkflowRepository(db, audit_service=None)


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
) -> RoleRepository:
    """Role repository for create/update/delete."""
    return RoleRepository(db, audit_service=None)


async def get_permission_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionRepository:
    """Permission repository for read operations and user/role assignment."""
    return PermissionRepository(db, audit_service=None)


async def get_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> PermissionRepository:
    """Permission repository for create/update/delete (transactional)."""
    return PermissionRepository(db, audit_service=None)


async def get_role_permission_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RolePermissionRepository:
    """Role–permission repository for read (e.g. get_permissions_for_role)."""
    return RolePermissionRepository(db, audit_service=None)


async def get_role_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> RolePermissionRepository:
    """Role–permission repository for assign/remove (transactional)."""
    return RolePermissionRepository(db, audit_service=None)


async def get_user_role_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRoleRepository:
    """User–role repository for read (e.g. get_user_roles)."""
    return UserRoleRepository(db, audit_service=None)


async def get_user_role_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> UserRoleRepository:
    """User–role repository for assign/remove (transactional)."""
    return UserRoleRepository(db, audit_service=None)


async def get_oauth_provider_config_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for read operations."""
    return OAuthProviderConfigRepository(db, audit_service=None)


async def get_oauth_provider_config_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for create/update/delete (transactional)."""
    return OAuthProviderConfigRepository(db, audit_service=None)


async def get_oauth_state_repo(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> OAuthStateRepository:
    """OAuth state repository for authorize/callback (transactional)."""
    return OAuthStateRepository(db)


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


# ---- Auth (current user from JWT) ----

_http_bearer = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
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
        return user
    except (ValueError, KeyError):
        return None


async def get_current_user(
    current_user: Annotated[object | None, Depends(get_current_user_optional)],
):
    """Return current user from JWT; raise 401 if missing or invalid."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


def require_permission(resource: str, action: str):
    """Dependency factory: require JWT auth and that the user has resource:action."""

    async def _require(
        current_user: Annotated[object, Depends(get_current_user)],
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> object:
        user_tenant = getattr(current_user, "tenant_id", None)
        if user_tenant != tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        user_id = getattr(current_user, "id", None)
        if not user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        await auth_svc.require_permission(user_id, tenant_id, resource, action)
        return current_user

    return _require
