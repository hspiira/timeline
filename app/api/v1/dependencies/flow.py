"""Flow and flow-document-compliance dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.flows import (
    CreateFlowUseCase,
    GetFlowDocumentComplianceUseCase,
)
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    DocumentCategoryRepository,
    DocumentRepository,
    DocumentRequirementRepository,
    FlowRepository,
    NamingTemplateRepository,
)

from . import document
from . import naming


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
        NamingTemplateRepository, Depends(naming.get_naming_template_repo)
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
        DocumentRequirementRepository, Depends(document.get_document_requirement_repo)
    ],
    document_category_repo: Annotated[
        DocumentCategoryRepository, Depends(document.get_document_category_repo)
    ],
    document_repo: Annotated[DocumentRepository, Depends(document.get_document_repo)],
) -> GetFlowDocumentComplianceUseCase:
    """Flow document compliance use case (required vs present docs)."""
    return GetFlowDocumentComplianceUseCase(
        flow_repo=flow_repo,
        document_requirement_repo=document_requirement_repo,
        document_category_repo=document_category_repo,
        document_repo=document_repo,
    )
