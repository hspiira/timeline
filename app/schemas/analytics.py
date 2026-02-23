"""Analytics/dashboard API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecentEventItem(BaseModel):
    """Minimal event summary for dashboard recent activity."""

    id: str
    subject_id: str
    event_type: str
    event_time: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class DashboardStatsResponse(BaseModel):
    """Dashboard stats: counts by type and last N events."""

    total_subjects: int
    subjects_by_type: dict[str, int] = Field(default_factory=dict)
    total_events: int
    events_by_type: dict[str, int] = Field(default_factory=dict)
    total_documents: int
    recent_events: list[RecentEventItem] = Field(default_factory=list)
