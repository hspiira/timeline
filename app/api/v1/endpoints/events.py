"""Event API: thin routes delegating to EventService and EventRepository."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_event_repo,
    get_event_service,
    get_tenant_id,
    get_verification_service,
    require_permission,
)
from app.application.services.verification_service import (
    ChainVerificationResult,
    VerificationService,
)
from app.application.use_cases.events import EventService
from app.core.limiter import limit_writes
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.schemas.event import (
    ChainVerificationResponse,
    EventCreate,
    EventListResponse,
    EventResponse,
    EventVerificationResult,
)

router = APIRouter()


def _to_verification_response(
    result: ChainVerificationResult,
) -> ChainVerificationResponse:
    """Map VerificationService result to API response schema."""
    return ChainVerificationResponse(
        subject_id=result.subject_id,
        tenant_id=result.tenant_id,
        total_events=result.total_events,
        valid_events=result.valid_events,
        invalid_events=result.invalid_events,
        is_chain_valid=result.is_chain_valid,
        verified_at=result.verified_at,
        event_results=[
            EventVerificationResult(
                event_id=er.event_id,
                event_type=er.event_type,
                event_time=er.event_time,
                sequence=er.sequence,
                is_valid=er.is_valid,
                error_type=er.error_type,
                error_message=er.error_message,
                expected_hash=er.expected_hash,
                actual_hash=er.actual_hash,
            )
            for er in result.event_results
        ],
    )


@router.post("", response_model=EventResponse, status_code=201)
@limit_writes
async def create_event(
    request: Request,
    body: EventCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_svc: Annotated[EventService, Depends(get_event_service)],
    _: Annotated[object, Depends(require_permission("event", "create"))] = None,
):
    """Create a single event (hash chaining, optional schema validation, workflows)."""
    try:
        created = await event_svc.create_event(tenant_id, body)
        return EventResponse(
            id=created.id,
            subject_id=created.subject_id,
            event_type=created.event_type.value,
            schema_version=body.schema_version,
            event_time=created.event_time,
            payload=created.payload,
            hash=created.chain.current_hash.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[EventListResponse])
async def list_events(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
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


@router.get("/count")
async def count_events(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Get total event count for the tenant (for dashboard stats)."""
    total = await event_repo.count_by_tenant(tenant_id)
    return {"total": total}


@router.get(
    "/verify/tenant/all",
    response_model=ChainVerificationResponse,
)
async def verify_tenant_chains(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    verification_svc: Annotated[VerificationService, Depends(get_verification_service)],
    limit: int = Query(1, ge=1, le=10000, description="Max events to verify"),
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Verify cryptographic integrity of all event chains for current tenant."""
    result = await verification_svc.verify_tenant_chains(
        tenant_id=tenant_id, limit=limit
    )
    return _to_verification_response(result)


@router.get(
    "/verify/{subject_id}",
    response_model=ChainVerificationResponse,
)
async def verify_subject_chain(
    subject_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    verification_svc: Annotated[VerificationService, Depends(get_verification_service)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Verify cryptographic integrity of event chain for a subject."""
    result = await verification_svc.verify_subject_chain(
        subject_id=subject_id, tenant_id=tenant_id
    )
    return _to_verification_response(result)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Get event by id (tenant-scoped)."""
    event = await event_repo.get_by_id_and_tenant(event_id, tenant_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event)
