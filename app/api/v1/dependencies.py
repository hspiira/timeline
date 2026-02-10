"""Presentation-layer dependency injection (composition root).

Provides FastAPI Depends() for DB sessions and application use cases.
All use cases are built from infrastructure implementations here;
routes depend only on these dependencies, not on infra directly.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.authorization_service import AuthorizationService
from app.application.services.hash_service import HashService
from app.application.use_cases.documents import DocumentService
from app.application.use_cases.events import EventService
from app.application.services.tenant_creation_service import TenantCreationService
from app.core.config import get_settings
from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.application.use_cases.subjects import SubjectService
from app.infrastructure.persistence.repositories import (
    DocumentRepository,
    EventRepository,
    EventSchemaRepository,
    SubjectRepository,
    TenantRepository,
    UserRepository,
    WorkflowRepository,
)
from app.infrastructure.services import (
    TenantInitializationService,
    WorkflowEngine,
)


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EventService:
    """Build EventService with hash chaining, schema validation, and workflow engine."""
    event_repo = EventRepository(db)
    hash_service = HashService()
    subject_repo = SubjectRepository(db)
    schema_repo = EventSchemaRepository(db)
    event_service = EventService(
        event_repo=event_repo,
        hash_service=hash_service,
        subject_repo=subject_repo,
        schema_repo=schema_repo,
        workflow_engine=None,
    )
    workflow_engine = WorkflowEngine(db, event_service)
    event_service.workflow_engine = workflow_engine
    return event_service


async def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> DocumentService:
    """Build DocumentService with storage and document/tenant repos."""
    storage = StorageFactory.create_storage_service()
    document_repo = DocumentRepository(db)
    tenant_repo = TenantRepository(db)
    return DocumentService(
        storage_service=storage,
        document_repo=document_repo,
        tenant_repo=tenant_repo,
    )


async def get_tenant_creation_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> TenantCreationService:
    """Build TenantCreationService for tenant + admin user + RBAC init."""
    tenant_repo = TenantRepository(db)
    user_repo = UserRepository(db)
    init_service = TenantInitializationService(db)
    return TenantCreationService(
        tenant_repo=tenant_repo,
        user_repo=user_repo,
        init_service=init_service,
    )


async def get_authorization_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthorizationService:
    """Build AuthorizationService with permission resolver and optional cache.

    Cache is set in app lifespan (app.state.cache) when Redis is enabled;
    otherwise cache is None and permission checks hit the DB only.
    """
    from app.infrastructure.services import PermissionResolver

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


async def get_tenant_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantRepository:
    """Tenant repository for read operations (list, get by id)."""
    return TenantRepository(db, cache_service=None, audit_service=None)


async def get_subject_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SubjectService:
    """Subject service for create/get/list (uses transactional session)."""
    subject_repo = SubjectRepository(db, audit_service=None)
    return SubjectService(subject_repo)


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    """User repository for read operations (list, get by id)."""
    return UserRepository(db, audit_service=None)


async def get_user_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> UserRepository:
    """User repository for create/update (transactional)."""
    return UserRepository(db, audit_service=None)


async def get_workflow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRepository:
    """Workflow repository for read operations (list, get by id)."""
    return WorkflowRepository(db, audit_service=None)


async def get_workflow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> WorkflowRepository:
    """Workflow repository for create (transactional)."""
    return WorkflowRepository(db, audit_service=None)
