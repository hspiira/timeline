"""Event schema API: thin routes delegating to event schema repository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_event_schema_repo,
    get_event_schema_repo_for_write,
    get_tenant_id,
    require_permission,
)
from app.application.dtos.user import UserResult
from app.application.interfaces.repositories import IEventSchemaRepository
from app.core.limiter import limit_writes
from app.schemas.event_schema import (
    EventSchemaCreateRequest,
    EventSchemaListItem,
    EventSchemaResponse,
    EventSchemaUpdate,
)

router = APIRouter()


@router.post("", response_model=EventSchemaResponse, status_code=201)
@limit_writes
async def create_event_schema(
    request: Request,
    body: EventSchemaCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult, Depends(require_permission("event_schema", "create"))],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo_for_write)],
):
    """Create a new event schema version (tenant-scoped). created_by from authenticated user."""
    try:
        schema = await schema_repo.create_schema(
            tenant_id=tenant_id,
            event_type=body.event_type,
            schema_definition=body.schema_definition,
            is_active=body.is_active,
            allowed_subject_types=body.allowed_subject_types,
            created_by=current_user.id,
        )
        return EventSchemaResponse.model_validate(schema)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[EventSchemaListItem])
async def list_all_schemas(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo)],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all event schema versions for the tenant (any event type)."""
    schemas = await schema_repo.get_all_for_tenant(
        tenant_id=tenant_id, skip=skip, limit=limit
    )
    return [EventSchemaListItem.model_validate(s) for s in schemas]


@router.get("/event-type/{event_type}", response_model=list[EventSchemaListItem])
async def list_schemas_by_event_type(
    event_type: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo)],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
):
    """List event schema versions for event_type (tenant-scoped)."""
    schemas = await schema_repo.get_all_for_event_type(
        tenant_id=tenant_id, event_type=event_type
    )
    return [EventSchemaListItem.model_validate(s) for s in schemas]


@router.get(
    "/event-type/{event_type}/active",
    response_model=EventSchemaResponse,
)
async def get_active_schema_for_event_type(
    event_type: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo)],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
):
    """Get active event schema for event_type (tenant-scoped)."""
    schema = await schema_repo.get_active_schema(
        tenant_id=tenant_id, event_type=event_type
    )
    if not schema:
        raise HTTPException(status_code=404, detail="Active schema not found")
    return EventSchemaResponse.model_validate(schema)


@router.get(
    "/event-type/{event_type}/version/{version}",
    response_model=EventSchemaResponse,
)
async def get_schema_by_version(
    event_type: str,
    version: int,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo)],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
):
    """Get event schema by event_type and version (tenant-scoped)."""
    schema = await schema_repo.get_by_version(
        tenant_id=tenant_id, event_type=event_type, version=version
    )
    if not schema:
        raise HTTPException(status_code=404, detail="Event schema not found")
    return EventSchemaResponse.model_validate(schema)


@router.get("/{schema_id}", response_model=EventSchemaResponse)
async def get_event_schema(
    schema_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo)],
    _: Annotated[object, Depends(require_permission("event_schema", "read"))] = None,
):
    """Get event schema by id (tenant-scoped)."""
    schema = await schema_repo.get_by_id(schema_id)
    if not schema or schema.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Event schema not found")
    return EventSchemaResponse.model_validate(schema)


@router.patch("/{schema_id}", response_model=EventSchemaResponse)
@limit_writes
async def update_event_schema(
    request: Request,
    schema_id: str,
    body: EventSchemaUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo_for_write)],
    _: Annotated[object, Depends(require_permission("event_schema", "update"))] = None,
):
    """Update event schema (schema_definition, is_active, allowed_subject_types). Tenant-scoped."""
    schema = await schema_repo.get_entity_by_id(schema_id)
    if not schema or schema.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Event schema not found")
    if body.schema_definition is not None:
        schema.schema_definition = body.schema_definition
    if body.is_active is not None:
        schema.is_active = body.is_active
    if body.allowed_subject_types is not None:
        schema.allowed_subject_types = body.allowed_subject_types
    updated = await schema_repo.update(schema)
    return EventSchemaResponse.model_validate(updated)


@router.delete("/{schema_id}", status_code=204)
@limit_writes
async def delete_event_schema(
    request: Request,
    schema_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: Annotated[IEventSchemaRepository, Depends(get_event_schema_repo_for_write)],
    _: Annotated[object, Depends(require_permission("event_schema", "delete"))] = None,
):
    """Delete event schema by id. Tenant-scoped."""
    schema = await schema_repo.get_entity_by_id(schema_id)
    if not schema or schema.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Event schema not found")
    await schema_repo.delete(schema)
