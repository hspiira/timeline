"""Flow domain entity.

A flow is a named instance of a workflow that groups many subjects
(and their events, tasks, documents). Flow.id is used as event.workflow_instance_id.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class FlowEntity:
    """Domain entity for a flow (workflow instance grouping)."""

    id: str
    tenant_id: str
    name: str
    workflow_id: str | None
    hierarchy_values: dict[str, str] | None  # level order -> value, e.g. {"1": "Renewals", "2": "2026"}

    def belongs_to_tenant(self, tenant_id: str) -> bool:
        """Return whether this flow belongs to the given tenant."""
        return self.tenant_id == tenant_id
