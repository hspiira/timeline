"""Analytics API: dashboard stats and projection-backed aggregations (Phase 5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.dependencies import (
    get_dashboard_stats_use_case,
    get_projection_repo,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.analytics import GetDashboardStatsUseCase
from app.infrastructure.persistence.repositories import ProjectionRepository
from app.schemas.analytics import DashboardStatsResponse, RecentEventItem
from app.schemas.projection import ProjectionStateListItem

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    use_case: Annotated[
        GetDashboardStatsUseCase, Depends(get_dashboard_stats_use_case)
    ],
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
):
    """Return dashboard stats for the tenant: counts by type and last 10 events."""
    stats = await use_case.get_dashboard_stats(tenant_id=tenant_id)
    return DashboardStatsResponse(
        total_subjects=stats.total_subjects,
        subjects_by_type=stats.subjects_by_type,
        total_events=stats.total_events,
        events_by_type=stats.events_by_type,
        total_documents=stats.total_documents,
        recent_events=[
            RecentEventItem(
                id=e.id,
                subject_id=e.subject_id,
                event_type=e.event_type,
                event_time=e.event_time,
                payload=e.payload,
            )
            for e in stats.recent_events
        ],
        chain_verification_info=(
            "Run verification per subject or tenant via POST /api/v1/events/verify-chain."
        ),
    )


@router.get(
    "/projections/{name}/{version}/summary",
    summary="Projection summary (total subjects)",
)
async def get_projection_summary(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    name: str,
    version: int,
    projection_repo: Annotated[
        ProjectionRepository, Depends(get_projection_repo)
    ],
    _: Annotated[object, Depends(require_permission("projection", "read"))] = None,
) -> dict:
    """Return aggregate summary for projection: total subject count."""
    defn = await projection_repo.get_by_name_version(
        tenant_id=tenant_id, name=name, version=version
    )
    if not defn:
        raise HTTPException(status_code=404, detail="Projection not found")
    total = await projection_repo.count_states(defn.id)
    return {"total_subjects": total}


@router.get(
    "/projections/{name}/{version}/top",
    response_model=list[ProjectionStateListItem],
    summary="Top subjects by projection state field",
)
async def get_projection_top(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    name: str,
    version: int,
    projection_repo: Annotated[
        ProjectionRepository, Depends(get_projection_repo)
    ],
    _: Annotated[object, Depends(require_permission("projection", "read"))] = None,
    field: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
) -> list[ProjectionStateListItem]:
    """Return top N subjects by numeric field in projection state (JSONB)."""
    defn = await projection_repo.get_by_name_version(
        tenant_id=tenant_id, name=name, version=version
    )
    if not defn:
        raise HTTPException(status_code=404, detail="Projection not found")
    states = await projection_repo.get_top_by_field(
        projection_id=defn.id, field=field, limit=limit
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
