"""Projection handler protocol (Phase 5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.application.dtos.event import EventResult


class IProjectionHandler(Protocol):
    """Protocol for projection handlers: apply one event to state, return new state."""

    async def __call__(self, state: dict, event: "EventResult") -> dict:
        """Apply one event to current state; return updated state.

        Must be pure with respect to state — do not mutate the input dict.
        """
        ...
