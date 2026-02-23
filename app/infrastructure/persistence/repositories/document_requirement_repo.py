"""Document requirement repository. Returns application DTOs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.document_requirement import DocumentRequirementResult
from app.infrastructure.persistence.models.document_requirement import (
    DocumentRequirement,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


def _to_result(r: DocumentRequirement) -> DocumentRequirementResult:
    """Map ORM to DocumentRequirementResult."""
    return DocumentRequirementResult(
        id=r.id,
        tenant_id=r.tenant_id,
        workflow_id=r.workflow_id,
        step_definition_id=r.step_definition_id,
        document_category_id=r.document_category_id,
        min_count=r.min_count,
    )


class DocumentRequirementRepository(BaseRepository[DocumentRequirement]):
    """Document requirement repository."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, DocumentRequirement)

    async def get_by_workflow(
        self,
        tenant_id: str,
        workflow_id: str,
        step_definition_id: str | None = None,
    ) -> list[DocumentRequirementResult]:
        """Return document requirements for workflow (and optional step)."""
        q = select(DocumentRequirement).where(
            DocumentRequirement.tenant_id == tenant_id,
            DocumentRequirement.workflow_id == workflow_id,
        )
        if step_definition_id is not None:
            q = q.where(
                DocumentRequirement.step_definition_id == step_definition_id
            )
        else:
            q = q.where(DocumentRequirement.step_definition_id.is_(None))
        result = await self.db.execute(q)
        return [_to_result(r) for r in result.scalars().all()]

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[DocumentRequirementResult]:
        """Return document requirements for tenant."""
        result = await self.db.execute(
            select(DocumentRequirement)
            .where(DocumentRequirement.tenant_id == tenant_id)
            .order_by(
                DocumentRequirement.workflow_id,
                DocumentRequirement.step_definition_id,
            )
            .offset(skip)
            .limit(limit)
        )
        return [_to_result(r) for r in result.scalars().all()]

    async def create(
        self,
        tenant_id: str,
        workflow_id: str,
        document_category_id: str,
        min_count: int = 1,
        step_definition_id: str | None = None,
    ) -> DocumentRequirementResult:
        """Create a document requirement."""
        r = DocumentRequirement(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            document_category_id=document_category_id,
            min_count=min_count,
            step_definition_id=step_definition_id,
        )
        created = await super().create(r)
        return _to_result(created)

    async def delete(self, requirement_id: str, tenant_id: str) -> bool:
        """Delete document requirement; return True if deleted."""
        result = await self.db.execute(
            select(DocumentRequirement).where(
                DocumentRequirement.id == requirement_id,
                DocumentRequirement.tenant_id == tenant_id,
            )
        )
        r = result.scalar_one_or_none()
        if not r:
            return False
        await self.db.delete(r)
        await self.db.flush()
        return True
