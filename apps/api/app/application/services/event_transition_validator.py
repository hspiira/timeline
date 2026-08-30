"""Validates that required prior event types have occurred before emitting an event type (implements IEventTransitionValidator)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.domain.exceptions import TransitionValidationException

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IEventRepository,
        IEventTransitionRuleRepository,
    )


def _last_event_of_type(events: list[Any], event_type: str) -> Any | None:
    """Return the last event in chronological list with given event_type, or None."""
    for i in range(len(events) - 1, -1, -1):
        if events[i].event_type == event_type:
            return events[i]
    return None


def _raise_transition(
    message: str,
    event_type: str,
    required_prior_event_types: list[str],
    **details_extra: Any,
) -> None:
    """Raise TransitionValidationException with common args and optional details."""
    raise TransitionValidationException(
        message=message,
        event_type=event_type,
        required_prior_event_types=required_prior_event_types,
        **details_extra,
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
        """Raise TransitionValidationException if a rule exists and conditions are not satisfied."""
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
            _raise_transition(
                f"Event type '{event_type}' requires prior event type(s) "
                f"{', '.join(repr(m) for m in missing)} for this subject.",
                event_type=event_type,
                required_prior_event_types=rule.required_prior_event_types,
            )

        if rule.prior_event_payload_conditions:
            req = rule.required_prior_event_types
            for prior_type, payload_map in rule.prior_event_payload_conditions.items():
                last_prior = _last_event_of_type(events, prior_type)
                if not last_prior:
                    _raise_transition(
                        f"Event type '{event_type}' requires prior event type "
                        f"'{prior_type}' for this subject.",
                        event_type=event_type,
                        required_prior_event_types=req,
                        reason="payload_condition_failed",
                        prior_event_type=prior_type,
                        expected_payload=payload_map,
                    )
                payload = getattr(last_prior, "payload", None) or {}
                for key, expected_value in payload_map.items():
                    if payload.get(key) != expected_value:
                        _raise_transition(
                            f"Event type '{event_type}' requires prior event type "
                            f"'{prior_type}' with payload.{key} = {expected_value!r}.",
                            event_type=event_type,
                            required_prior_event_types=req,
                            reason="payload_condition_failed",
                            prior_event_type=prior_type,
                            expected_payload=payload_map,
                        )

        if rule.max_occurrences_per_stream is not None:
            count = sum(1 for e in events if e.event_type == event_type)
            if count >= rule.max_occurrences_per_stream:
                _raise_transition(
                    f"Event type '{event_type}' may appear at most "
                    f"{rule.max_occurrences_per_stream} time(s) per stream.",
                    event_type=event_type,
                    required_prior_event_types=rule.required_prior_event_types,
                    reason="max_occurrences_per_stream",
                    max=rule.max_occurrences_per_stream,
                )

        if rule.fresh_prior_event_type:
            last_current = _last_event_of_type(events, event_type)
            last_fresh = _last_event_of_type(
                events, rule.fresh_prior_event_type
            )
            if last_current is not None:
                if last_fresh is None or last_fresh.event_time <= last_current.event_time:
                    _raise_transition(
                        f"Event type '{event_type}' requires a new "
                        f"'{rule.fresh_prior_event_type}' after the previous "
                        f"'{event_type}'.",
                        event_type=event_type,
                        required_prior_event_types=rule.required_prior_event_types,
                        reason="fresh_prior_required",
                        fresh_prior_event_type=rule.fresh_prior_event_type,
                    )
