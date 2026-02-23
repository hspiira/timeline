"""Subject, subject-type, relationship, and snapshot dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.subject_type_schema_validator import (
    SubjectTypeSchemaValidator,
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
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    DocumentRepository,
    EventRepository,
    RelationshipKindRepository,
    SubjectRelationshipRepository,
    SubjectRepository,
    SubjectSnapshotRepository,
    SubjectTypeRepository,
)
from app.infrastructure.services import SystemAuditService

from . import document
from . import event
from . import tenant
from . import db as db_deps


async def get_subject_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
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
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> SubjectRepository:
    """Subject repository for update/delete (transactional, tenant-scoped)."""
    return SubjectRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )


async def get_subject_export_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
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
    document_repo: Annotated[
        DocumentRepository, Depends(document.get_document_repo_for_write)
    ],
) -> SubjectErasureService:
    """Subject erasure use case (anonymize or delete)."""
    return SubjectErasureService(
        subject_repo=subject_repo,
        document_repo=document_repo,
    )


async def get_subject_relationship_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
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
    event_service = event._build_event_service_for_session(db, tenant_id, audit_svc)
    relationship_kind_repo = RelationshipKindRepository(db)
    return SubjectRelationshipService(
        relationship_repo=relationship_repo,
        subject_repo=subject_repo,
        event_service=event_service,
        relationship_kind_repo=relationship_kind_repo,
    )


async def get_subject_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
) -> SubjectRepository:
    """Subject repository for read operations (tenant-scoped, no audit)."""
    return SubjectRepository(db, tenant_id=tenant_id, audit_service=None)


async def get_get_subject_state_use_case(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
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
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
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
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
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
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> SubjectTypeRepository:
    """Subject type repository for create/update/delete (transactional)."""
    return SubjectTypeRepository(db, audit_service=audit_svc)
