"""Workflow API: thin routes delegating to WorkflowRepository and WorkflowExecutionRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.dependencies import (
    get_tenant_id,
    get_workflow_execution_repo,
    get_workflow_repo,
    get_workflow_repo_for_write,
)
from app.infrastructure.persistence.repositories.workflow_repo import (
    WorkflowExecutionRepository,
    WorkflowRepository,
)
from app.schemas.workflow import (
    WorkflowCreateRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)

router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    body: WorkflowCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
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
):
    """Get execution history for a workflow. Tenant-scoped."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
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
):
    """Get workflow execution by id. Tenant-scoped."""
    execution = await execution_repo.get_by_id(execution_id, tenant_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return WorkflowExecutionResponse.model_validate(execution)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
):
    """Get workflow by id (tenant-scoped)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
):
    """Update workflow (tenant-scoped)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
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
async def delete_workflow(
    workflow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
):
    """Soft-delete workflow. Tenant-scoped."""
    result = await workflow_repo.soft_delete(workflow_id, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
):
    """List workflows for tenant (paginated)."""
    workflows = await workflow_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
    )
    return [WorkflowResponse.model_validate(w) for w in workflows]
