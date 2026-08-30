"""Create flow use case: optional naming template validation and hierarchy parsing."""

from __future__ import annotations

from app.application.dtos.flow import FlowResult
from app.application.interfaces.repositories import (
    IFlowRepository,
    INamingTemplateRepository,
)
from app.application.services.naming_template_validator import validate_and_parse
from app.domain.exceptions import ResourceNotFoundException, ValidationException


class CreateFlowUseCase:
    """Creates a flow with optional naming template validation and subject linking."""

    def __init__(
        self,
        flow_repo: IFlowRepository,
        naming_template_repo: INamingTemplateRepository,
    ) -> None:
        self._flow_repo = flow_repo
        self._naming_template_repo = naming_template_repo

    async def execute(
        self,
        tenant_id: str,
        name: str,
        *,
        workflow_id: str | None = None,
        hierarchy_values: dict[str, str] | None = None,
        subject_ids: list[str] | None = None,
        subject_roles: dict[str, str] | None = None,
    ) -> FlowResult:
        """Create a flow; validate name against workflow naming template if present.

        Args:
            tenant_id: Tenant id.
            name: Flow name.
            workflow_id: Optional workflow id (for template lookup).
            hierarchy_values: Optional hierarchy; if None and template exists, parsed from name.
            subject_ids: Optional subject ids to link.
            subject_roles: Optional subject_id -> role map.

        Returns:
            Created flow result.

        Raises:
            ValidationException: If template exists and name does not match.
            ResourceNotFoundException: If referenced workflow/subject not found (from repo).
        """
        if workflow_id:
            template = await self._naming_template_repo.get_for_scope(
                tenant_id=tenant_id,
                scope_type="flow",
                scope_id=workflow_id,
            )
            if template:
                parsed = validate_and_parse(
                    name,
                    template.template_string,
                    template.placeholders,
                )
                if hierarchy_values is None:
                    hierarchy_values = parsed
        flow = await self._flow_repo.create_flow(
            tenant_id=tenant_id,
            name=name,
            workflow_id=workflow_id,
            hierarchy_values=hierarchy_values,
            subject_ids=subject_ids,
            subject_roles=subject_roles,
        )
        return flow
