"""Event API: thin routes delegating to EventService and EventRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.v1.dependencies import get_event_repo, get_event_service
from app.application.use_cases.events import EventService
from app.core.config import get_settings
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.schemas.event import EventCreate

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


@router.post("", status_code=201)
async def create_event(
    body: EventCreate,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    event_svc: Annotated[EventService, Depends(get_event_service)],
):
    """Create a single event (hash chaining, optional schema validation, workflows)."""
    try:
        created = await event_svc.create_event(tenant_id, body)
        return {"id": created.id, "event_type": created.event_type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_events(
    tenant_id: Annotated[str, Depends(_tenant_id)],
    subject_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    event_repo: EventRepository = Depends(get_event_repo),
):
    """List events for tenant; optionally filter by subject_id."""
    if subject_id:
        events = await event_repo.get_by_subject(
            subject_id=subject_id,
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
        )
    else:
        events = await event_repo.get_by_tenant(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
        )
    return [
        {
            "id": e.id,
            "subject_id": e.subject_id,
            "event_type": e.event_type,
            "event_time": e.event_time.isoformat(),
        }
        for e in events
    ]


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    tenant_id: Annotated[str, Depends(_tenant_id)],
    event_repo: EventRepository = Depends(get_event_repo),
):
    """Get event by id (tenant-scoped)."""
    event = await event_repo.get_by_id_and_tenant(event_id, tenant_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": event.id,
        "subject_id": event.subject_id,
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "event_time": event.event_time.isoformat(),
        "payload": event.payload,
        "hash": event.hash,
    }
