"""Workflow and workflow-execution dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    WorkflowExecutionRepository,
    WorkflowRepository,
)
from app.infrastructure.services import SystemAuditService

from . import db as db_deps


async def get_workflow_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRepository:
    """Workflow repository for read operations (list, get by id)."""
    return WorkflowRepository(db, audit_service=None)


async def get_workflow_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> WorkflowRepository:
    """Workflow repository for create/update/delete (transactional)."""
    return WorkflowRepository(db, audit_service=audit_svc)


async def get_workflow_execution_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionRepository:
    """Workflow execution repository for read (list by workflow, get by id)."""
    return WorkflowExecutionRepository(db)
