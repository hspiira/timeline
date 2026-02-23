"""Document and document-category dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.documents import (
    DocumentQueryService,
    DocumentUploadService,
    RunDocumentRetentionUseCase,
)
from app.application.services.document_category_metadata_validator import (
    DocumentCategoryMetadataValidator,
)
from app.infrastructure.external.storage.factory import StorageFactory
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    DocumentCategoryRepository,
    DocumentRepository,
    DocumentRequirementRepository,
    TenantRepository,
)
from app.infrastructure.services import SystemAuditService
from . import tenant
from . import db as db_deps


async def get_document_upload_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
    tenant_repo: Annotated[TenantRepository, Depends(tenant.get_tenant_repo)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> DocumentUploadService:
    """Build DocumentUploadService for upload (storage + document/tenant repos + optional category metadata validation)."""
    from app.infrastructure.persistence.repositories import SubjectRepository

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
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> DocumentRepository:
    """Document repository for update/soft-delete."""
    return DocumentRepository(db, audit_service=audit_svc)


async def get_run_document_retention_use_case(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
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
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
) -> DocumentCategoryRepository:
    """Document category repository for read operations (tenant-scoped)."""
    return DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=None
    )


async def get_document_category_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> DocumentCategoryRepository:
    """Document category repository for create/update/delete (transactional, tenant-scoped)."""
    return DocumentCategoryRepository(
        db, tenant_id=tenant_id, audit_service=audit_svc
    )
