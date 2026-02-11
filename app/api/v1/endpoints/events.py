"""Event API: thin routes delegating to EventService and EventRepository."""

import asyncio
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.dependencies import (
    get_event_repo,
    get_event_service,
    get_tenant_id,
    get_verification_service,
    require_permission,
)
from app.application.dtos.event import CreateEventCommand
from app.application.services.verification_service import (
    ChainVerificationResult,
    VerificationService,
)
from app.application.use_cases.events import EventService
from app.core.limiter import limit_writes
from app.domain.exceptions import VerificationLimitExceededException
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.application.services.hash_service import HashService
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
from app.shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_verification_job(app, job_id: str) -> None:
    """Background task: run tenant verification and store result in app.state.verification_jobs."""
    jobs = getattr(app, "state", None) and getattr(app.state, "verification_jobs", None)
    if not jobs or job_id not in jobs:
        return
    job = jobs[job_id]
    tenant_id = job.get("tenant_id")
    if not tenant_id:
        job["status"] = "failed"
        job["error"] = "Missing tenant_id"
        return
    job["status"] = "running"
    session_gen = get_db()
    try:
        session = await session_gen.__anext__()
    except StopAsyncIteration:
        await session_gen.aclose()
        job["status"] = "failed"
        job["error"] = "Failed to obtain database session"
        return
    try:
        event_repo = EventRepository(session)
        svc = VerificationService(
            event_repo=event_repo,
            hash_service=HashService(),
            max_events=None,
            timeout_seconds=None,
        )
        result = await svc.verify_tenant_chains(tenant_id=tenant_id)
        job["status"] = "completed"
        job["result"] = result
    except Exception as e:
        logger.exception("Verification job %s failed: %s", job_id, e)
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        await session_gen.aclose()


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
):
    """Create a single event (hash chaining, optional schema validation, workflows)."""
    cmd = CreateEventCommand(
        subject_id=body.subject_id,
        event_type=body.event_type,
        schema_version=body.schema_version,
        event_time=body.event_time,
        payload=body.payload,
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
    except asyncio.TimeoutError:
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
    _: Annotated[object, Depends(require_permission("event", "read"))] = None,
):
    """Start a background verification job for all tenant event chains (for large tenants). Poll GET /events/verify/tenant/jobs/{job_id} for status."""
    app = request.app
    if not hasattr(app.state, "verification_jobs"):
        app.state.verification_jobs = {}
    job_id = str(uuid.uuid4())
    app.state.verification_jobs[job_id] = {
        "tenant_id": tenant_id,
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": utc_now(),
    }
    asyncio.create_task(_run_verification_job(app, job_id))
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
    jobs = getattr(request.app.state, "verification_jobs", None) or {}
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job.get("tenant_id") != tenant_id:
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
