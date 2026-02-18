"""Workflow domain entity.

A workflow is a definition: trigger (event type + conditions) and actions.
Flows are named instances of a workflow that group many subjects.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowEntity:
    """Domain entity for a workflow definition (trigger + actions)."""

    id: str
    tenant_id: str
    name: str
    description: str | None
    is_active: bool
    trigger_event_type: str
    trigger_conditions: dict[str, Any] | None
    actions: list[dict[str, Any]]
    max_executions_per_day: int | None
    execution_order: int

    def belongs_to_tenant(self, tenant_id: str) -> bool:
        """Return whether this workflow belongs to the given tenant."""
        return self.tenant_id == tenant_id

    def can_trigger_on(self, event_type: str) -> bool:
        """Return whether this workflow is active and matches the event type."""
        return self.is_active and self.trigger_event_type == event_type
