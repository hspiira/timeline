"""Analytics use case: dashboard stats (counts and recent activity)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.analytics import DashboardStats

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IDocumentRepository,
        IEventRepository,
        ISubjectRepository,
    )


class GetDashboardStatsUseCase:
    """Get aggregate stats and recent events for tenant dashboard."""

    def __init__(
        self,
        subject_repo: "ISubjectRepository",
        event_repo: "IEventRepository",
        document_repo: "IDocumentRepository",
    ) -> None:
        self.subject_repo = subject_repo
        self.event_repo = event_repo
        self.document_repo = document_repo

    async def get_dashboard_stats(self, tenant_id: str) -> DashboardStats:
        """Return counts by type and last N events for the tenant."""
        total_subjects = await self.subject_repo.count_by_tenant(tenant_id)
        subjects_by_type = await self.subject_repo.get_counts_by_type(tenant_id)
        total_events = await self.event_repo.count_by_tenant(tenant_id)
        events_by_type = await self.event_repo.get_counts_by_type(tenant_id)
        total_documents = await self.document_repo.count_by_tenant(tenant_id)
        recent_events = await self.event_repo.get_by_tenant(
            tenant_id, skip=0, limit=10
        )
        return DashboardStats(
            total_subjects=total_subjects,
            subjects_by_type=subjects_by_type,
            total_events=total_events,
            events_by_type=events_by_type,
            total_documents=total_documents,
            recent_events=recent_events,
        )
