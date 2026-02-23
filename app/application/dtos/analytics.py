"""DTOs for analytics/dashboard (no dependency on ORM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.dtos.event import EventResult


@dataclass
class DashboardStats:
    """Dashboard stats for a tenant: counts, recent activity, and timeline-integrity guidance."""

    total_subjects: int
    subjects_by_type: dict[str, int]
    total_events: int
    events_by_type: dict[str, int]
    total_documents: int
    recent_events: list["EventResult"]
    chain_verification_info: str | None = None
