"""DTOs for document requirements (required vs present check)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentRequirementResult:
    """Single document requirement (workflow + optional step + category + min_count)."""

    id: str
    tenant_id: str
    workflow_id: str
    step_definition_id: str | None
    document_category_id: str
    min_count: int


@dataclass(frozen=True)
class DocumentComplianceItem:
    """Required vs present for one document category in a flow."""

    document_category_id: str
    category_name: str
    display_name: str
    required_count: int
    present_count: int
    satisfied: bool
    blocked_reason: str | None  # e.g. "Missing: 2 required, 1 present"


@dataclass(frozen=True)
class FlowDocumentComplianceResult:
    """Result of document compliance check for a flow."""

    flow_id: str
    items: list[DocumentComplianceItem]
    all_satisfied: bool
    blocked_reasons: list[str]  # summary of what is missing
