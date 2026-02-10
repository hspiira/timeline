"""Workflow API: thin routes delegating to WorkflowRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_workflow_repo, get_workflow_repo_for_write, get_tenant_id
from app.infrastructure.persistence.repositories.workflow_repo import WorkflowRepository
from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse

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
