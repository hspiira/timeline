"""Audit projection: global event count (all subject types)."""

from __future__ import annotations

from app.application.dtos.event import EventResult
from app.core.projections import projection


@projection("global_event_count", subject_type=None)
async def global_event_count(state: dict, _event: EventResult) -> dict:
    """Increment a global event counter for the tenant (all subjects).

    State shape: {"count": int}.
    """
    count = state.get("count", 0)
    return {"count": count + 1}
