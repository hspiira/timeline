"""Validates that required prior event types have occurred before emitting an event type (implements IEventTransitionValidator)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.exceptions import TransitionValidationException

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IEventRepository,
        IEventTransitionRuleRepository,
    )


class EventTransitionValidator:
    """Checks transition rules: event_type may require prior event types in the stream."""

    def __init__(
        self,
        rule_repo: IEventTransitionRuleRepository,
        event_repo: IEventRepository,
    ) -> None:
        self._rule_repo = rule_repo
        self._event_repo = event_repo

    async def validate_can_emit(
        self,
        tenant_id: str,
        subject_id: str,
        event_type: str,
        workflow_instance_id: str | None = None,
    ) -> None:
        """Raise TransitionValidationException if a rule exists and required prior event types are missing."""
        rule = await self._rule_repo.get_rule_for_event_type(tenant_id, event_type)
        if not rule:
            return

        events = await self._event_repo.get_events_chronological(
            subject_id=subject_id,
            tenant_id=tenant_id,
            workflow_instance_id=workflow_instance_id,
        )
        seen_types: set[str] = {e.event_type for e in events}

        missing = [t for t in rule.required_prior_event_types if t not in seen_types]
        if missing:
            raise TransitionValidationException(
                message=(
                    f"Event type '{event_type}' requires prior event type(s) "
                    f"{', '.join(repr(m) for m in missing)} for this subject."
                ),
                event_type=event_type,
                required_prior_event_types=rule.required_prior_event_types,
            )
