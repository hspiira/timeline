"""Get flow document compliance use case: required vs present documents for flow subjects."""

from __future__ import annotations

from app.application.dtos.document_requirement import (
    DocumentComplianceItem,
    FlowDocumentComplianceResult,
)
from app.application.interfaces.repositories import (
    IDocumentCategoryRepository,
    IDocumentRepository,
    IDocumentRequirementRepository,
    IFlowRepository,
)
from app.domain.exceptions import ResourceNotFoundException


class GetFlowDocumentComplianceUseCase:
    """Computes document compliance for a flow (flow-level requirements only)."""

    def __init__(
        self,
        flow_repo: IFlowRepository,
        document_requirement_repo: IDocumentRequirementRepository,
        document_category_repo: IDocumentCategoryRepository,
        document_repo: IDocumentRepository,
    ) -> None:
        self._flow_repo = flow_repo
        self._document_requirement_repo = document_requirement_repo
        self._document_category_repo = document_category_repo
        self._document_repo = document_repo

    async def execute(
        self,
        tenant_id: str,
        flow_id: str,
    ) -> FlowDocumentComplianceResult:
        """Return required vs present documents for the flow's subjects.

        Args:
            tenant_id: Tenant id.
            flow_id: Flow id.

        Returns:
            Compliance result with items, all_satisfied, blocked_reasons.

        Raises:
            ResourceNotFoundException: If flow is not found.
        """
        flow = await self._flow_repo.get_by_id(flow_id, tenant_id)
        if not flow:
            raise ResourceNotFoundException("flow", flow_id)
        subject_links = await self._flow_repo.list_subjects_for_flow(
            flow_id, tenant_id
        )
        subject_ids = [s.subject_id for s in subject_links]
        items: list[DocumentComplianceItem] = []
        blocked_reasons: list[str] = []
        if flow.workflow_id:
            requirements = await self._document_requirement_repo.get_by_workflow(
                tenant_id=tenant_id,
                workflow_id=flow.workflow_id,
                step_definition_id=None,
            )
            for req in requirements:
                category = await self._document_category_repo.get_by_id(
                    req.document_category_id
                )
                if not category or category.tenant_id != tenant_id:
                    category_name = "unknown"
                    display_name = "Unknown category"
                else:
                    category_name = category.category_name
                    display_name = category.display_name
                present = await self._document_repo.count_by_subjects_and_document_type(
                    tenant_id=tenant_id,
                    subject_ids=subject_ids,
                    document_type=category_name,
                )
                satisfied = present >= req.min_count
                blocked_reason = None
                if not satisfied:
                    blocked_reason = (
                        f"Missing: {req.min_count} required, {present} present"
                    )
                    blocked_reasons.append(f"{display_name}: {blocked_reason}")
                items.append(
                    DocumentComplianceItem(
                        document_category_id=req.document_category_id,
                        category_name=category_name,
                        display_name=display_name,
                        required_count=req.min_count,
                        present_count=present,
                        satisfied=satisfied,
                        blocked_reason=blocked_reason,
                    )
                )
        return FlowDocumentComplianceResult(
            flow_id=flow_id,
            items=items,
            all_satisfied=len(blocked_reasons) == 0,
            blocked_reasons=blocked_reasons,
        )
