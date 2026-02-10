"""Event API: thin routes delegating to EventService and EventRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import get_event_repo, get_event_service, get_tenant_id
from app.application.use_cases.events import EventService
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.schemas.event import EventCreate, EventListResponse, EventResponse

router = APIRouter()


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    body: EventCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_svc: Annotated[EventService, Depends(get_event_service)],
):
    """Create a single event (hash chaining, optional schema validation, workflows)."""
    try:
        created = await event_svc.create_event(tenant_id, body)
        return EventResponse.model_validate(created)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[EventListResponse])
async def list_events(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    subject_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
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
    return [EventListResponse.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
):
    """Get event by id (tenant-scoped)."""
    event = await event_repo.get_by_id_and_tenant(event_id, tenant_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event)
