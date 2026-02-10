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
