"""Event API: thin routes delegating to EventService and EventRepository."""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    ensure_audit_logged,
    get_event_repo,
    get_event_service,
    get_tenant_id,
    get_verification_service,
    get_verification_runner,
    require_permission,
)
from app.application.dtos.event import EventCreate
from app.application.services.verification_service import (
    ChainVerificationResult,
    VerificationService,
)
from app.application.use_cases.events import EventService
from app.core.limiter import limit_writes
from app.domain.exceptions import VerificationLimitExceededException
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.schemas.event import (
    ChainVerificationResponse,
    EventCountResponse,
    EventCreateRequest,
    EventListResponse,
    EventResponse,
    EventVerificationResult,
    VerificationJobStartedResponse,
    VerificationJobStatusResponse,
)
logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_verification_job(
    app,
    job_id: str,
    run_verification: Callable[[str], Awaitable[ChainVerificationResult]],
) -> None:
    """Background task: run tenant verification and store result in verification_job_store."""
    store = getattr(app.state, "verification_job_store", None)
    if not store:
        return
    job = store.get(job_id)
    if not job:
        return
    tenant_id = job.get("tenant_id")
    if not tenant_id:
        store.update(job_id, "failed", error="Missing tenant_id")
        return
    store.update(job_id, "running")
    try:
        result = await run_verification(tenant_id)
        store.update(job_id, "completed", result=result)
    except Exception as e:
        logger.exception("Verification job %s failed", job_id)
        store.update(job_id, "failed", error=str(e))


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
    body: EventCreateRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_svc: Annotated[EventService, Depends(get_event_service)],
    _: Annotated[object, Depends(require_permission("event", "create"))] = None,
    _audit: Annotated[object, Depends(ensure_audit_logged)] = None,
):
    """Create a single event (hash chaining, optional schema validation, workflows)."""
    cmd = EventCreate(
        subject_id=body.subject_id,
        event_type=body.event_type,
        schema_version=body.schema_version,
        event_time=body.event_time,
        payload=body.payload,
        workflow_instance_id=body.workflow_instance_id,
        correlation_id=body.correlation_id,
    )
    try:
        created = await event_svc.create_event(tenant_id, cmd)
        return EventResponse(
            id=created.id,
            subject_id=created.subject_id,
            event_type=created.event_type.value,
            schema_version=cmd.schema_version,
            event_time=created.event_time,
            payload=created.payload,
            hash=created.chain.current_hash.value,
            workflow_instance_id=created.workflow_instance_id,
            correlation_id=created.correlation_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[EventListResponse])
async def list_events(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
    subject_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
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


@router.get(
    "/count",
    response_model=EventCountResponse,
)
async def count_events(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    event_repo: Annotated[EventRepository, Depends(get_event_repo)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Get total event count for the tenant (for dashboard stats)."""
    total = await event_repo.count_by_tenant(tenant_id)
    return EventCountResponse(total=total)


@router.get(
    "/verify/tenant/all",
    response_model=ChainVerificationResponse,
)
async def verify_tenant_chains(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    verification_svc: Annotated[VerificationService, Depends(get_verification_service)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Verify cryptographic integrity of all event chains for current tenant (inline; use POST /verify/tenant/all/start for large tenants)."""
    try:
        result = await verification_svc.verify_tenant_chains(tenant_id=tenant_id)
        return _to_verification_response(result)
    except VerificationLimitExceededException as e:
        raise HTTPException(
            status_code=400,
            detail=f"{e.message} Use POST /events/verify/tenant/all/start to run verification in the background.",
        ) from e
    except TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Verification timed out. Use POST /events/verify/tenant/all/start to run verification in the background.",
        ) from None


@router.post(
    "/verify/tenant/all/start",
    response_model=VerificationJobStartedResponse,
    status_code=202,
)
async def start_verification_job(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    run_verification: Annotated[
        Callable[[str], Awaitable[ChainVerificationResult]],
        Depends(get_verification_runner),
    ],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Start a background verification job for all tenant event chains (for large tenants). Poll GET /events/verify/tenant/jobs/{job_id} for status."""
    store = request.app.state.verification_job_store
    job_id = str(uuid.uuid4())
    store.set(job_id, tenant_id)
    asyncio.create_task(_run_verification_job(request.app, job_id, run_verification))
    return VerificationJobStartedResponse(job_id=job_id)


@router.get(
    "/verify/tenant/jobs/{job_id}",
    response_model=VerificationJobStatusResponse,
)
async def get_verification_job_status(
    job_id: str,
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Get status and result of a background verification job (tenant-scoped: only own tenant's jobs)."""
    store = getattr(request.app.state, "verification_job_store", None)
    if not store:
        raise HTTPException(status_code=404, detail="Job not found")
    job = store.get(job_id)
    if not job or job.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job["status"]
    result = job.get("result")
    error = job.get("error")
    total_events = result.total_events if result else None
    return VerificationJobStatusResponse(
        job_id=job_id,
        status=status,
        result=_to_verification_response(result) if result else None,
        error=error,
        total_events=total_events,
    )


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
    try:
        result = await verification_svc.verify_subject_chain(
            subject_id=subject_id, tenant_id=tenant_id
        )
        return _to_verification_response(result)
    except VerificationLimitExceededException as e:
        raise HTTPException(
            status_code=429,
            detail=e.message,
        ) from e
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Verification timed out.",
        ) from None


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
