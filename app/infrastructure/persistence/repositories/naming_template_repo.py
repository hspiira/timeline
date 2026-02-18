"""Naming template repository. Returns application DTOs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.naming_template import NamingTemplateResult
from app.infrastructure.persistence.models.naming_template import NamingTemplate
from app.infrastructure.persistence.repositories.base import BaseRepository


def _to_result(t: NamingTemplate) -> NamingTemplateResult:
    """Map ORM to NamingTemplateResult."""
    return NamingTemplateResult(
        id=t.id,
        tenant_id=t.tenant_id,
        scope_type=t.scope_type,
        scope_id=t.scope_id,
        template_string=t.template_string,
        placeholders=t.placeholders,
    )


class NamingTemplateRepository(BaseRepository[NamingTemplate]):
    """Naming template repository. All access tenant-scoped via parameters."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, NamingTemplate)

    async def get_by_id(
        self, template_id: str, tenant_id: str
    ) -> NamingTemplateResult | None:
        """Return naming template by ID if it belongs to tenant."""
        result = await self.db.execute(
            select(NamingTemplate).where(
                NamingTemplate.id == template_id,
                NamingTemplate.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_for_scope(
        self, tenant_id: str, scope_type: str, scope_id: str
    ) -> NamingTemplateResult | None:
        """Return naming template for (tenant, scope_type, scope_id), or None."""
        result = await self.db.execute(
            select(NamingTemplate).where(
                NamingTemplate.tenant_id == tenant_id,
                NamingTemplate.scope_type == scope_type,
                NamingTemplate.scope_id == scope_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[NamingTemplateResult]:
        """Return naming templates for tenant with pagination."""
        result = await self.db.execute(
            select(NamingTemplate)
            .where(NamingTemplate.tenant_id == tenant_id)
            .order_by(NamingTemplate.scope_type, NamingTemplate.scope_id)
            .offset(skip)
            .limit(limit)
        )
        return [_to_result(t) for t in result.scalars().all()]

    async def create(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        template_string: str,
        placeholders: list[dict[str, Any]] | None = None,
    ) -> NamingTemplateResult:
        """Create a naming template. Raises if duplicate (tenant, scope_type, scope_id)."""
        t = NamingTemplate(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            template_string=template_string,
            placeholders=placeholders,
        )
        created = await super().create(t)
        return _to_result(created)

    async def update(
        self,
        template_id: str,
        tenant_id: str,
        *,
        template_string: str | None = None,
        placeholders: list[dict[str, Any]] | None = None,
    ) -> NamingTemplateResult | None:
        """Update template; return updated result or None if not found."""
        result = await self.db.execute(
            select(NamingTemplate).where(
                NamingTemplate.id == template_id,
                NamingTemplate.tenant_id == tenant_id,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return None
        if template_string is not None:
            t.template_string = template_string
        if placeholders is not None:
            t.placeholders = placeholders
        await self.db.flush()
        await self.db.refresh(t)
        return _to_result(t)

    async def delete(self, template_id: str, tenant_id: str) -> bool:
        """Delete naming template; return True if deleted."""
        result = await self.db.execute(
            select(NamingTemplate).where(
                NamingTemplate.id == template_id,
                NamingTemplate.tenant_id == tenant_id,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return False
        await self.db.delete(t)
        await self.db.flush()
        return True
