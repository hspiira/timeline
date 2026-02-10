"""Event schema API: thin routes delegating to EventSchemaRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_event_schema_repo, get_event_schema_repo_for_write
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.event_schema_repo import (
    EventSchemaRepository,
)
from app.schemas.event_schema import EventSchemaCreateRequest, EventSchemaResponse

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


@router.post("", response_model=EventSchemaResponse, status_code=201)
async def create_event_schema(
    body: EventSchemaCreateRequest,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo_for_write),
):
    """Create a new event schema version (tenant-scoped)."""
    try:
        schema = await schema_repo.create_schema(
            tenant_id=tenant_id,
            event_type=body.event_type,
            schema_definition=body.schema_definition,
            is_active=body.is_active,
            created_by=body.created_by,
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
        raise HTTPException(status_code=400, detail=str(e))


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


@router.get("")
async def list_event_schemas(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    event_type: str,
    schema_repo: EventSchemaRepository = Depends(get_event_schema_repo),
):
    """List event schema versions for event_type (tenant-scoped)."""
    schemas = await schema_repo.get_all_for_event_type(
        tenant_id=tenant_id,
        event_type=event_type,
    )
    return [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "event_type": s.event_type,
            "version": s.version,
            "is_active": s.is_active,
            "created_by": s.created_by,
        }
        for s in schemas
    ]
