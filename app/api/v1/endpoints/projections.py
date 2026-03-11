"""Projection API: definitions and state (Phase 5)."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.dependencies import (
    get_projection_management_use_case,
    get_projection_read_permission,
    get_projection_write_permission,
    get_query_projection_use_case,
    get_tenant_id,
    get_verified_tenant_id,
)
from app.application.use_cases.projections import (
    ProjectionManagementUseCase,
    QueryProjectionUseCase,
)
from app.schemas.projection import (
    ProjectionDefinitionCreateRequest,
    ProjectionDefinitionResponse,
    ProjectionStateListItem,
    ProjectionStateResponse,
)

router = APIRouter()


def _definition_to_response(r: Any) -> ProjectionDefinitionResponse:
    """Map DTO to response schema."""
    return ProjectionDefinitionResponse(
        id=r.id,
        tenant_id=r.tenant_id,
        name=r.name,
        version=r.version,
        subject_type=r.subject_type,
        last_event_seq=r.last_event_seq,
        active=r.active,
        created_at=r.created_at,
    )


@router.post(
    "/{tenant_id}/projections",
    response_model=ProjectionDefinitionResponse,
    status_code=201,
    summary="Create projection definition",
)
async def create_projection(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    body: ProjectionDefinitionCreateRequest,
    use_case: Annotated[
        ProjectionManagementUseCase, Depends(get_projection_management_use_case)
    ],
    _: Annotated[object, Depends(get_projection_write_permission)] = None,
) -> ProjectionDefinitionResponse:
    """Create a projection definition; engine will build it automatically."""
    created = await use_case.create_projection(
        tenant_id=tenant_id,
        name=body.name,
        version=body.version,
        subject_type=body.subject_type,
    )
    return _definition_to_response(created)


@router.get(
    "/{tenant_id}/projections",
    response_model=list[ProjectionDefinitionResponse],
    summary="List projection definitions",
)
async def list_projections(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    use_case: Annotated[
        ProjectionManagementUseCase, Depends(get_projection_management_use_case)
    ],
    _: Annotated[object, Depends(get_projection_read_permission)] = None,
) -> list[ProjectionDefinitionResponse]:
    """List all projection definitions for the tenant (active and inactive)."""
    definitions = await use_case.list_projections(tenant_id=tenant_id)
    return [_definition_to_response(d) for d in definitions]


@router.delete(
    "/{tenant_id}/projections/{name}/{version}",
    status_code=204,
    summary="Deactivate projection",
)
async def deactivate_projection(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    name: str,
    version: int,
    use_case: Annotated[
        ProjectionManagementUseCase, Depends(get_projection_management_use_case)
    ],
    _: Annotated[object, Depends(get_projection_write_permission)] = None,
) -> None:
    """Set active=False; engine will skip this projection."""
    if version < 1:
        raise HTTPException(status_code=400, detail="version must be >= 1")
    await use_case.deactivate_projection(
        tenant_id=tenant_id, name=name, version=version
    )


@router.post(
    "/{tenant_id}/projections/{name}/{version}/rebuild",
    status_code=202,
    summary="Rebuild projection",
)
async def rebuild_projection(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    name: str,
    version: int,
    use_case: Annotated[
        ProjectionManagementUseCase, Depends(get_projection_management_use_case)
    ],
    _: Annotated[object, Depends(get_projection_write_permission)] = None,
) -> None:
    """Reset watermark to 0; engine will replay from genesis on next cycle."""
    if version < 1:
        raise HTTPException(status_code=400, detail="version must be >= 1")
    await use_case.rebuild_projection(
        tenant_id=tenant_id, name=name, version=version
    )


@router.get(
    "/{tenant_id}/projections/{name}/{version}/subjects/{subject_id}",
    response_model=ProjectionStateResponse,
    summary="Get projection state for subject",
)
async def get_projection_state(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    name: str,
    version: int,
    subject_id: str,
    use_case: Annotated[
        QueryProjectionUseCase, Depends(get_query_projection_use_case)
    ],
    _: Annotated[object, Depends(get_projection_read_permission)] = None,
    as_of: datetime | None = Query(
        default=None,
        description="Point-in-time state (replay); omit for current state",
    ),
) -> ProjectionStateResponse:
    """Return projection state for subject (current or as_of replay)."""
    if as_of is not None:
        state = await use_case.get_state_as_of(
            tenant_id=tenant_id,
            name=name,
            version=version,
            subject_id=subject_id,
            as_of=as_of,
        )
    else:
        state = await use_case.get_current_state(
            tenant_id=tenant_id,
            name=name,
            version=version,
            subject_id=subject_id,
        )
    if state is None:
        raise HTTPException(status_code=404, detail="Projection state not found")
    return ProjectionStateResponse(subject_id=subject_id, state=state)


@router.get(
    "/{tenant_id}/projections/{name}/{version}/states",
    response_model=list[ProjectionStateListItem],
    summary="List all projection states",
)
async def list_projection_states(
    tenant_id: Annotated[str, Depends(get_verified_tenant_id)],
    name: str,
    version: int,
    use_case: Annotated[
        QueryProjectionUseCase, Depends(get_query_projection_use_case)
    ],
    _: Annotated[object, Depends(get_projection_read_permission)] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[ProjectionStateListItem]:
    """List all subjects' current state for this projection (paginated)."""
    states = await use_case.list_all_states(
        tenant_id=tenant_id,
        name=name,
        version=version,
        skip=skip,
        limit=limit,
    )
    return [
        ProjectionStateListItem(
            id=s.id,
            projection_id=s.projection_id,
            subject_id=s.subject_id,
            state=s.state,
            updated_at=s.updated_at,
        )
        for s in states
    ]
