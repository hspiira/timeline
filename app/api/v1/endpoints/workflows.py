"""Workflow API: thin routes delegating to WorkflowRepository and WorkflowExecutionRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_document_requirement_repo,
    get_document_requirement_repo_for_write,
    get_tenant_id,
    get_workflow_execution_repo,
    get_workflow_repo,
    get_workflow_repo_for_write,
    require_permission,
)
from app.application.interfaces.repositories import IDocumentRequirementRepository
from app.core.limiter import limit_writes
from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.repositories.workflow_repo import (
    WorkflowExecutionRepository,
    WorkflowRepository,
)
from app.schemas.document_requirement import (
    DocumentRequirementCreateRequest,
    DocumentRequirementResponse,
)
from app.schemas.workflow import (
    WorkflowCreateRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)

router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=201)
@limit_writes
async def create_workflow(
    request: Request,
    body: WorkflowCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
    _: Annotated[object, Depends(require_permission("workflow", "create"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Create a workflow (tenant-scoped)."""
    try:
        workflow = await workflow_repo.create_workflow(
            tenant_id=tenant_id,
            name=body.name,
            trigger_event_type=body.trigger_event_type,
            actions=[a.model_dump() for a in body.actions],
            description=body.description,
            is_active=body.is_active,
            trigger_conditions=body.trigger_conditions,
            max_executions_per_day=body.max_executions_per_day,
            execution_order=body.execution_order,
        )
        return WorkflowResponse.model_validate(workflow)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{workflow_id}/executions",
    response_model=list[WorkflowExecutionResponse],
)
async def get_workflow_executions(
    workflow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    execution_repo: WorkflowExecutionRepository = Depends(
        get_workflow_execution_repo
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: Annotated[object, Depends(require_permission("workflow", "read"))] = None,
):
    """Get execution history for a workflow. Tenant-scoped."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise ResourceNotFoundException("workflow", workflow_id)
    executions = await execution_repo.get_by_workflow(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return [WorkflowExecutionResponse.model_validate(e) for e in executions]


@router.get(
    "/executions/{execution_id}",
    response_model=WorkflowExecutionResponse,
)
async def get_execution(
    execution_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    execution_repo: WorkflowExecutionRepository = Depends(
        get_workflow_execution_repo
    ),
    _: Annotated[object, Depends(require_permission("workflow", "read"))] = None,
):
    """Get workflow execution by id. Tenant-scoped."""
    execution = await execution_repo.get_by_id(execution_id, tenant_id)
    if not execution:
        raise ResourceNotFoundException("workflow_execution", execution_id)
    return WorkflowExecutionResponse.model_validate(execution)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    _: Annotated[object, Depends(require_permission("workflow", "read"))] = None,
):
    """Get workflow by id (tenant-scoped)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise ResourceNotFoundException("workflow", workflow_id)
    return WorkflowResponse.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
@limit_writes
async def update_workflow(
    request: Request,
    workflow_id: str,
    body: WorkflowUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
    _: Annotated[object, Depends(require_permission("workflow", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Update workflow (tenant-scoped)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise ResourceNotFoundException("workflow", workflow_id)
    if body.name is not None:
        workflow.name = body.name
    if body.description is not None:
        workflow.description = body.description
    if body.is_active is not None:
        workflow.is_active = body.is_active
    if body.trigger_conditions is not None:
        workflow.trigger_conditions = body.trigger_conditions
    if body.max_executions_per_day is not None:
        workflow.max_executions_per_day = body.max_executions_per_day
    if body.execution_order is not None:
        workflow.execution_order = body.execution_order
    updated = await workflow_repo.update(workflow)
    return WorkflowResponse.model_validate(updated)


@router.delete("/{workflow_id}", status_code=204)
@limit_writes
async def delete_workflow(
    request: Request,
    workflow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
    _: Annotated[object, Depends(require_permission("workflow", "delete"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Soft-delete workflow. Tenant-scoped."""
    result = await workflow_repo.soft_delete(workflow_id, tenant_id)
    if not result:
        raise ResourceNotFoundException("workflow", workflow_id)


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = False,
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    _: Annotated[object, Depends(require_permission("workflow", "read"))] = None,
):
    """List workflows for tenant (paginated)."""
    workflows = await workflow_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
    )
    return [WorkflowResponse.model_validate(w) for w in workflows]


@router.get(
    "/{workflow_id}/document-requirements",
    response_model=list[DocumentRequirementResponse],
)
async def list_workflow_document_requirements(
    workflow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_requirement_repo: Annotated[
        IDocumentRequirementRepository, Depends(get_document_requirement_repo)
    ],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    _: Annotated[object, Depends(require_permission("workflow", "read"))] = None,
):
    """List document requirements for a workflow (flow-level only)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise ResourceNotFoundException("workflow", workflow_id)
    requirements = await document_requirement_repo.get_by_workflow(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        step_definition_id=None,
    )
    return [DocumentRequirementResponse.model_validate(r) for r in requirements]


@router.post(
    "/{workflow_id}/document-requirements",
    response_model=DocumentRequirementResponse,
    status_code=201,
)
@limit_writes
async def create_workflow_document_requirement(
    request: Request,
    workflow_id: str,
    body: DocumentRequirementCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_requirement_repo: Annotated[
        IDocumentRequirementRepository,
        Depends(get_document_requirement_repo_for_write),
    ],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    _: Annotated[object, Depends(require_permission("workflow", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Add a document requirement to a workflow (flow-level)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise ResourceNotFoundException("workflow", workflow_id)
    requirement = await document_requirement_repo.create(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        document_category_id=body.document_category_id,
        min_count=body.min_count,
        step_definition_id=None,
    )
    return DocumentRequirementResponse.model_validate(requirement)


@router.delete("/document-requirements/{requirement_id}", status_code=204)
@limit_writes
async def delete_document_requirement(
    request: Request,
    requirement_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    document_requirement_repo: Annotated[
        IDocumentRequirementRepository,
        Depends(get_document_requirement_repo_for_write),
    ],
    _: Annotated[object, Depends(require_permission("workflow", "update"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Delete a document requirement."""
    deleted = await document_requirement_repo.delete(
        requirement_id=requirement_id, tenant_id=tenant_id
    )
    if not deleted:
        raise ResourceNotFoundException("document_requirement", requirement_id)
