"""DTOs for flow (workflow instance grouping)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FlowResult:
    """Flow read-model (result of get_by_id, get_by_tenant, create_flow, etc.)."""

    id: str
    tenant_id: str
    name: str
    workflow_id: str | None
    created_at: datetime
    updated_at: datetime
    hierarchy_values: dict[str, str] | None  # level order -> value


@dataclass(frozen=True)
class FlowSubjectResult:
    """Flow-subject link (subject_id in a flow, optional role)."""

    flow_id: str
    subject_id: str
    role: str | None
