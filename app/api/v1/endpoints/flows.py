"""Flow API: thin routes delegating to use cases and repositories."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import (
    get_create_flow_use_case,
    get_event_repo,
    get_flow_document_compliance_use_case,
    get_flow_repo,
    get_flow_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.interfaces.repositories import (
    IEventRepository,
    IFlowRepository,
)
from app.application.use_cases.flows import (
    CreateFlowUseCase,
    GetFlowDocumentComplianceUseCase,
)
from app.domain.exceptions import ResourceNotFoundException
from app.schemas.event import EventResponse
from app.schemas.flow import (
    DocumentComplianceItemResponse,
    FlowAddSubjectsRequest,
    FlowCreateRequest,
    FlowDocumentComplianceResponse,
    FlowResponse,
    FlowSubjectResponse,
    FlowUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=FlowResponse, status_code=201)
async def create_flow(
    body: FlowCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    create_flow_uc: Annotated[
        CreateFlowUseCase, Depends(get_create_flow_use_case)
    ],
    _: Annotated[object, Depends(require_permission("flow", "create"))] = None,
):
    """Create a flow (tenant-scoped). Optionally link subjects. Name validated against naming template if one exists for this workflow."""
    flow = await create_flow_uc.execute(
        tenant_id=tenant_id,
        name=body.name,
        workflow_id=body.workflow_id,
        hierarchy_values=body.hierarchy_values,
        subject_ids=body.subject_ids,
        subject_roles=body.subject_roles,
    )
    return FlowResponse.model_validate(flow)


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo)],
    _: Annotated[object, Depends(require_permission("flow", "read"))] = None,
):
    """Get flow by id (tenant-scoped)."""
    flow = await flow_repo.get_by_id(flow_id, tenant_id)
    if not flow:
        raise ResourceNotFoundException("flow", flow_id)
    return FlowResponse.model_validate(flow)


@router.get("", response_model=list[FlowResponse])
async def list_flows(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    workflow_id: str | None = None,
    _: Annotated[object, Depends(require_permission("flow", "read"))] = None,
):
    """List flows for tenant (paginated). Optional filter by workflow_id."""
    flows = await flow_repo.get_by_tenant(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        workflow_id=workflow_id,
    )
    return [FlowResponse.model_validate(f) for f in flows]


@router.put("/{flow_id}", response_model=FlowResponse)
async def update_flow(
    flow_id: str,
    body: FlowUpdateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo_for_write)],
    _: Annotated[object, Depends(require_permission("flow", "update"))] = None,
):
    """Update flow name or hierarchy_values (tenant-scoped)."""
    flow = await flow_repo.update_flow(
        flow_id=flow_id,
        tenant_id=tenant_id,
        name=body.name,
        hierarchy_values=body.hierarchy_values,
    )
    if not flow:
        raise ResourceNotFoundException("flow", flow_id)
    return FlowResponse.model_validate(flow)


@router.get("/{flow_id}/subjects", response_model=list[FlowSubjectResponse])
async def list_flow_subjects(
    flow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo)],
    _: Annotated[object, Depends(require_permission("flow", "read"))] = None,
):
    """List subjects linked to the flow."""
    flow = await flow_repo.get_by_id(flow_id, tenant_id)
    if not flow:
        raise ResourceNotFoundException("flow", flow_id)
    links = await flow_repo.list_subjects_for_flow(flow_id, tenant_id)
    return [FlowSubjectResponse.model_validate(l) for l in links]


@router.post("/{flow_id}/subjects")
async def add_subjects_to_flow(
    flow_id: str,
    body: FlowAddSubjectsRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo_for_write)],
    _: Annotated[object, Depends(require_permission("flow", "update"))] = None,
):
    """Add subjects to a flow."""
    await flow_repo.add_subjects_to_flow(
        flow_id=flow_id,
        tenant_id=tenant_id,
        subject_ids=body.subject_ids,
        roles=body.roles,
    )


@router.delete("/{flow_id}/subjects/{subject_id}", status_code=204)
async def remove_subject_from_flow(
    flow_id: str,
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo_for_write)],
    _: Annotated[object, Depends(require_permission("flow", "update"))] = None,
):
    """Remove a subject from a flow."""
    removed = await flow_repo.remove_subject_from_flow(
        flow_id=flow_id, subject_id=subject_id, tenant_id=tenant_id
    )
    if not removed:
        raise ResourceNotFoundException("flow", flow_id)


@router.get(
    "/{flow_id}/document-compliance",
    response_model=FlowDocumentComplianceResponse,
)
async def get_flow_document_compliance(
    flow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    use_case: Annotated[
        GetFlowDocumentComplianceUseCase,
        Depends(get_flow_document_compliance_use_case),
    ],
    _: Annotated[object, Depends(require_permission("flow", "read"))] = None,
):
    """Return required vs present documents for this flow (flow-level requirements only)."""
    result = await use_case.execute(tenant_id=tenant_id, flow_id=flow_id)
    return FlowDocumentComplianceResponse(
        flow_id=result.flow_id,
        items=[
            DocumentComplianceItemResponse.model_validate(i) for i in result.items
        ],
        all_satisfied=result.all_satisfied,
        blocked_reasons=result.blocked_reasons,
    )


@router.get("/{flow_id}/events", response_model=list[EventResponse])
async def list_flow_events(
    flow_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    flow_repo: Annotated[IFlowRepository, Depends(get_flow_repo)],
    event_repo: Annotated[IEventRepository, Depends(get_event_repo)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: Annotated[object, Depends(require_permission("flow", "read"))] = None,
):
    """List events for this flow (events where workflow_instance_id = flow_id)."""
    flow = await flow_repo.get_by_id(flow_id, tenant_id)
    if not flow:
        raise ResourceNotFoundException("flow", flow_id)
    events = await event_repo.get_by_workflow_instance_id(
        tenant_id=tenant_id,
        workflow_instance_id=flow_id,
        skip=skip,
        limit=limit,
    )
    return [EventResponse.model_validate(e) for e in events]
