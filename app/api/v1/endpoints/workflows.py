"""Workflow API: thin routes delegating to WorkflowRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_workflow_repo, get_workflow_repo_for_write
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.workflow_repo import WorkflowRepository
from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse

router = APIRouter()


def _tenant_id(x_tenant_id: str | None = Header(None)) -> str:
    """Resolve tenant ID from header; raise 400 if missing."""
    name = get_settings().tenant_header_name
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {name}",
        )
    return x_tenant_id


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    body: WorkflowCreateRequest,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo_for_write),
):
    """Create a workflow (tenant-scoped)."""
    try:
        workflow = await workflow_repo.create_workflow(
            tenant_id=tenant_id,
            name=body.name,
            trigger_event_type=body.trigger_event_type,
            actions=body.actions,
            description=body.description,
            is_active=body.is_active,
            trigger_conditions=body.trigger_conditions,
            max_executions_per_day=body.max_executions_per_day,
            execution_order=body.execution_order,
        )
        return WorkflowResponse(
            id=workflow.id,
            tenant_id=workflow.tenant_id,
            name=workflow.name,
            description=workflow.description,
            is_active=workflow.is_active,
            trigger_event_type=workflow.trigger_event_type,
            trigger_conditions=workflow.trigger_conditions,
            actions=workflow.actions,
            max_executions_per_day=workflow.max_executions_per_day,
            execution_order=workflow.execution_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
):
    """Get workflow by id (tenant-scoped)."""
    workflow = await workflow_repo.get_by_id_and_tenant(workflow_id, tenant_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse(
        id=workflow.id,
        tenant_id=workflow.tenant_id,
        name=workflow.name,
        description=workflow.description,
        is_active=workflow.is_active,
        trigger_event_type=workflow.trigger_event_type,
        trigger_conditions=workflow.trigger_conditions,
        actions=workflow.actions,
        max_executions_per_day=workflow.max_executions_per_day,
        execution_order=workflow.execution_order,
    )


@router.get("")
async def list_workflows(
    tenant_id: Annotated[str, Depends(_tenant_id)],
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
    return [
        {
            "id": w.id,
            "tenant_id": w.tenant_id,
            "name": w.name,
            "description": w.description,
            "is_active": w.is_active,
            "trigger_event_type": w.trigger_event_type,
            "execution_order": w.execution_order,
        }
        for w in workflows
    ]
