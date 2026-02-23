"""Retention API: on-demand run of document category-based retention (soft-delete)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.v1.dependencies import (
    get_run_document_retention_use_case,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.documents import RunDocumentRetentionUseCase
from app.core.limiter import limit_writes
from app.schemas.retention import RetentionRunResponse

router = APIRouter()


@router.post("/run", response_model=RetentionRunResponse)
@limit_writes
async def run_retention(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    retention_use_case: Annotated[
        RunDocumentRetentionUseCase, Depends(get_run_document_retention_use_case)
    ],
    _: Annotated[object, Depends(require_permission("document", "delete"))] = None,
):
    """Run document retention for the current tenant.

    For each document category that has default_retention_days set, soft-deletes
    documents whose document_type matches the category and whose created_at is
    older than (now - default_retention_days). Returns a summary of how many
    documents were soft-deleted per category.
    """
    result = await retention_use_case.run(tenant_id=tenant_id)
    return RetentionRunResponse(
        tenant_id=result.tenant_id,
        soft_deleted_by_category=result.soft_deleted_by_category,
        total_soft_deleted=result.total_soft_deleted,
    )
