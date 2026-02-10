"""Event schema API: thin routes delegating to EventSchemaRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_current_user,
    get_event_schema_repo,
    get_event_schema_repo_for_write,
    get_tenant_id,
)
from app.infrastructure.persistence.repositories.event_schema_repo import (
    EventSchemaRepository,
)
from app.schemas.event_schema import (
    EventSchemaCreateRequest,
    EventSchemaListItem,
    EventSchemaResponse,
    EventSchemaUpdate,
)

router = APIRouter()


@router.post("", response_model=EventSchemaResponse, status_code=201)
async def create_event_schema(
    body: EventSchemaCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[object, Depends(get_current_user)],
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo_for_write),
):
    """Create a new event schema version (tenant-scoped). created_by is set from the authenticated user."""
    try:
        schema = await schema_repo.create_schema(
            tenant_id=tenant_id,
            event_type=body.event_type,
            schema_definition=body.schema_definition,
            is_active=body.is_active,
            created_by=getattr(current_user, "id", None),
        )
        return EventSchemaResponse(
            id=schema.id,
            tenant_id=schema.tenant_id,
            event_type=schema.event_type,
            version=schema.version,
            is_active=schema.is_active,
            schema_definition=schema.schema_definition,
            created_by=schema.created_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/event-type/{event_type}", response_model=list[EventSchemaListItem])
async def list_schemas_by_event_type(
    event_type: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo),
):
    """List event schema versions for event_type (tenant-scoped)."""
    schemas = await schema_repo.get_all_for_event_type(
        tenant_id=tenant_id, event_type=event_type
    )
    return [
        EventSchemaListItem(
            id=s.id,
            tenant_id=s.tenant_id,
            event_type=s.event_type,
            version=s.version,
            is_active=s.is_active,
            created_by=s.created_by,
        )
        for s in schemas
    ]


@router.get(
    "/event-type/{event_type}/active",
    response_model=EventSchemaResponse,
)
async def get_active_schema_for_event_type(
    event_type: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo),
):
    """Get active event schema for event_type (tenant-scoped)."""
    schema = await schema_repo.get_active_schema(
        tenant_id=tenant_id, event_type=event_type
    )
    if not schema:
        raise HTTPException(status_code=404, detail="Active schema not found")
    return EventSchemaResponse(
        id=schema.id,
        tenant_id=schema.tenant_id,
        event_type=schema.event_type,
        version=schema.version,
        is_active=schema.is_active,
        schema_definition=schema.schema_definition,
        created_by=schema.created_by,
    )


@router.get(
    "/event-type/{event_type}/version/{version}",
    response_model=EventSchemaResponse,
)
async def get_schema_by_version(
    event_type: str,
    version: int,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo),
):
    """Get event schema by event_type and version (tenant-scoped)."""
    schema = await schema_repo.get_by_version(
        tenant_id=tenant_id, event_type=event_type, version=version
    )
    if not schema:
        raise HTTPException(status_code=404, detail="Event schema not found")
    return EventSchemaResponse(
        id=schema.id,
        tenant_id=schema.tenant_id,
        event_type=schema.event_type,
        version=schema.version,
        is_active=schema.is_active,
        schema_definition=schema.schema_definition,
        created_by=schema.created_by,
    )


@router.get("/{schema_id}", response_model=EventSchemaResponse)
async def get_event_schema(
    schema_id: str,
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo),
):
    """Get event schema by id."""
    schema = await schema_repo.get_by_id(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Event schema not found")
    return EventSchemaResponse(
        id=schema.id,
        tenant_id=schema.tenant_id,
        event_type=schema.event_type,
        version=schema.version,
        is_active=schema.is_active,
        schema_definition=schema.schema_definition,
        created_by=schema.created_by,
    )


@router.patch("/{schema_id}", response_model=EventSchemaResponse)
async def update_event_schema(
    schema_id: str,
    body: EventSchemaUpdate,
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo_for_write),
):
    """Update event schema (schema_definition and/or is_active)."""
    schema = await schema_repo.get_entity_by_id(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Event schema not found")
    if body.schema_definition is not None:
        schema.schema_definition = body.schema_definition
    if body.is_active is not None:
        schema.is_active = body.is_active
    updated = await schema_repo.update(schema)
    return EventSchemaResponse(
        id=updated.id,
        tenant_id=updated.tenant_id,
        event_type=updated.event_type,
        version=updated.version,
        is_active=updated.is_active,
        schema_definition=updated.schema_definition,
        created_by=updated.created_by,
    )


@router.delete("/{schema_id}", status_code=204)
async def delete_event_schema(
    schema_id: str,
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo_for_write),
):
    """Delete event schema by id."""
    schema = await schema_repo.get_entity_by_id(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Event schema not found")
    await schema_repo.delete(schema)


@router.get("", response_model=list[EventSchemaListItem])
async def list_event_schemas(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_type: str,
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo),
):
    """List event schema versions for event_type (tenant-scoped)."""
    schemas = await schema_repo.get_all_for_event_type(
        tenant_id=tenant_id,
        event_type=event_type,
    )
    return [
        EventSchemaListItem(
            id=s.id,
            tenant_id=s.tenant_id,
            event_type=s.event_type,
            version=s.version,
            is_active=s.is_active,
            created_by=s.created_by,
        )
        for s in schemas
    ]
