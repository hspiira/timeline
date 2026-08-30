"""Post-create hook protocol for event side effects (workflow, webhook, SSE).

Allows EventService to run post-creation concerns without coupling to concrete
implementations. New concerns (e.g. audit, analytics) add a hook; EventService
does not change (OCP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.application.dtos.event import EventResult
    from app.domain.entities.event import EventEntity


@dataclass(frozen=True)
class PostCreateContext:
    """Context passed to each post-create hook after one event is persisted."""

    tenant_id: str
    entity: "EventEntity"
    event_result: "EventResult"
    subject_type: str
    trigger_workflows: bool


class IPostCreateHook(Protocol):
    """Protocol for side effects after an event is created (workflow, webhook, SSE)."""

    async def after_event(self, context: PostCreateContext) -> None:
        """Run after one event has been persisted. Must not fail the request."""
        ...
