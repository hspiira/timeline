"""EventTransitionRule repository. Returns application DTOs."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.event_transition_rule import EventTransitionRuleResult
from app.domain.exceptions import ValidationException
from app.infrastructure.persistence.models.event_transition_rule import (
    EventTransitionRule,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


_OPTIONAL_RESULT_ATTRS = (
    "prior_event_payload_conditions",
    "max_occurrences_per_stream",
    "fresh_prior_event_type",
)


def _to_result(r: EventTransitionRule) -> EventTransitionRuleResult:
    """Map ORM EventTransitionRule to EventTransitionRuleResult."""
    optional = {a: getattr(r, a, None) for a in _OPTIONAL_RESULT_ATTRS}
    return EventTransitionRuleResult(
        id=r.id,
        tenant_id=r.tenant_id,
        event_type=r.event_type,
        required_prior_event_types=r.required_prior_event_types or [],
        description=r.description,
        **optional,
    )


class EventTransitionRuleRepository(BaseRepository[EventTransitionRule]):
    """Event transition rule repository. Tenant-scoped by query."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, EventTransitionRule)

    async def get_by_id(self, rule_id: str) -> EventTransitionRuleResult | None:
        """Return rule by id."""
        row = await super().get_by_id(rule_id)
        return _to_result(row) if row else None

    async def get_by_id_and_tenant(
        self, rule_id: str, tenant_id: str
    ) -> EventTransitionRuleResult | None:
        """Return rule by id if it belongs to tenant."""
        result = await self.db.execute(
            select(EventTransitionRule).where(
                EventTransitionRule.id == rule_id,
                EventTransitionRule.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_rule_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> EventTransitionRuleResult | None:
        """Return the transition rule for (tenant_id, event_type), or None."""
        result = await self.db.execute(
            select(EventTransitionRule).where(
                EventTransitionRule.tenant_id == tenant_id,
                EventTransitionRule.event_type == event_type,
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventTransitionRuleResult]:
        """Return all transition rules for tenant."""
        result = await self.db.execute(
            select(EventTransitionRule)
            .where(EventTransitionRule.tenant_id == tenant_id)
            .order_by(EventTransitionRule.event_type.asc())
            .offset(skip)
            .limit(limit)
        )
        return [_to_result(r) for r in result.scalars().all()]

    async def _get_orm_by_id_and_tenant(
        self, rule_id: str, tenant_id: str
    ) -> EventTransitionRule | None:
        """Load rule ORM by id and tenant (internal use for update/delete)."""
        result = await self.db.execute(
            select(EventTransitionRule).where(
                EventTransitionRule.id == rule_id,
                EventTransitionRule.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_rule(
        self,
        tenant_id: str,
        event_type: str,
        required_prior_event_types: list[str],
        description: str | None = None,
        prior_event_payload_conditions: dict | None = None,
        max_occurrences_per_stream: int | None = None,
        fresh_prior_event_type: str | None = None,
    ) -> EventTransitionRuleResult:
        """Create a transition rule. Raises ValidationException if (tenant_id, event_type) already exists."""
        existing = await self.get_rule_for_event_type(tenant_id, event_type)
        if existing:
            raise ValidationException(
                f"Transition rule for event_type '{event_type}' already exists for this tenant",
                field="event_type",
            )
        rule = EventTransitionRule(
            tenant_id=tenant_id,
            event_type=event_type,
            required_prior_event_types=required_prior_event_types,
            description=description,
            prior_event_payload_conditions=prior_event_payload_conditions,
            max_occurrences_per_stream=max_occurrences_per_stream,
            fresh_prior_event_type=fresh_prior_event_type,
        )
        created = await self.create(rule)
        return _to_result(created)

    async def update_rule(
        self,
        rule_id: str,
        tenant_id: str,
        *,
        required_prior_event_types: list[str] | None = None,
        description: str | None = None,
        prior_event_payload_conditions: dict | None = None,
        max_occurrences_per_stream: int | None = None,
        fresh_prior_event_type: str | None = None,
    ) -> EventTransitionRuleResult | None:
        """Update rule by id and tenant; return updated result or None if not found."""
        rule = await self._get_orm_by_id_and_tenant(rule_id, tenant_id)
        if not rule:
            return None
        if required_prior_event_types is not None:
            rule.required_prior_event_types = required_prior_event_types
        if description is not None:
            rule.description = description
        if prior_event_payload_conditions is not None:
            rule.prior_event_payload_conditions = prior_event_payload_conditions
        if max_occurrences_per_stream is not None:
            rule.max_occurrences_per_stream = max_occurrences_per_stream
        if fresh_prior_event_type is not None:
            rule.fresh_prior_event_type = fresh_prior_event_type
        updated = await super().update(rule, skip_existence_check=True)
        return _to_result(updated)

    async def delete_rule(self, rule_id: str, tenant_id: str) -> bool:
        """Delete rule by id and tenant. Return True if deleted, False if not found."""
        rule = await self._get_orm_by_id_and_tenant(rule_id, tenant_id)
        if not rule:
            return False
        await self.delete(rule)
        return True

    async def update(
        self, obj: EventTransitionRule, *, skip_existence_check: bool = False
    ) -> EventTransitionRule:
        """Update rule. Returns updated ORM (caller may convert to result)."""
        return await super().update(obj, skip_existence_check=skip_existence_check)
