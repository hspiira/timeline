"""Analytics API: dashboard stats (counts and recent activity)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import (
    get_dashboard_stats_use_case,
    get_tenant_id,
    require_permission,
)
from app.application.use_cases.analytics import GetDashboardStatsUseCase
from app.schemas.analytics import DashboardStatsResponse, RecentEventItem

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
        chain_verification_info=stats.chain_verification_info,
    )
