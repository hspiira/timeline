"""Relationship kind repository. CRUD for tenant-configured relationship kinds."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.relationship_kind import RelationshipKindResult
from app.domain.exceptions import ValidationException
from app.infrastructure.persistence.models.relationship_kind import RelationshipKind
from app.shared.utils.generators import generate_cuid


def _to_result(r: RelationshipKind) -> RelationshipKindResult:
    """Map ORM to DTO."""
    return RelationshipKindResult(
        id=r.id,
        tenant_id=r.tenant_id,
        kind=r.kind,
        display_name=r.display_name,
        description=r.description,
        payload_schema=r.payload_schema,
    )


class RelationshipKindRepository:
    """Repository for relationship kinds. No tenant scope at construction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_tenant(
        self, tenant_id: str
    ) -> list[RelationshipKindResult]:
        """Return all configured relationship kinds for the tenant."""
        result = await self.db.execute(
            select(RelationshipKind)
            .where(RelationshipKind.tenant_id == tenant_id)
            .order_by(RelationshipKind.kind.asc())
        )
        return [_to_result(r) for r in result.scalars().all()]

    async def get_by_id(
        self, kind_id: str
    ) -> RelationshipKindResult | None:
        """Return relationship kind by ID."""
        result = await self.db.execute(
            select(RelationshipKind).where(RelationshipKind.id == kind_id)
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_by_tenant_and_kind(
        self, tenant_id: str, kind: str
    ) -> RelationshipKindResult | None:
        """Return relationship kind by tenant and kind string."""
        result = await self.db.execute(
            select(RelationshipKind).where(
                RelationshipKind.tenant_id == tenant_id,
                RelationshipKind.kind == kind,
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def create(
        self,
        tenant_id: str,
        kind: str,
        display_name: str,
        description: str | None = None,
        payload_schema: dict | None = None,
    ) -> RelationshipKindResult:
        """Create a relationship kind; raise if duplicate kind for tenant."""
        existing = await self.get_by_tenant_and_kind(tenant_id, kind)
        if existing:
            raise ValidationException(
                f"Relationship kind '{kind}' already exists for this tenant",
                field="kind",
            )
        entity = RelationshipKind(
            id=generate_cuid(),
            tenant_id=tenant_id,
            kind=kind,
            display_name=display_name,
            description=description,
            payload_schema=payload_schema,
        )
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return _to_result(entity)

    async def update(
        self,
        kind_id: str,
        tenant_id: str,
        display_name: str | None = None,
        description: str | None = None,
        payload_schema: dict | None = None,
    ) -> RelationshipKindResult | None:
        """Update relationship kind; return None if not found or wrong tenant."""
        result = await self.db.execute(
            select(RelationshipKind).where(RelationshipKind.id == kind_id)
        )
        entity = result.scalar_one_or_none()
        if not entity or entity.tenant_id != tenant_id:
            return None
        if display_name is not None:
            entity.display_name = display_name
        if description is not None:
            entity.description = description
        if payload_schema is not None:
            entity.payload_schema = payload_schema
        await self.db.flush()
        await self.db.refresh(entity)
        return _to_result(entity)

    async def delete(self, kind_id: str, tenant_id: str) -> bool:
        """Delete relationship kind; return True if deleted."""
        result = await self.db.execute(
            select(RelationshipKind).where(RelationshipKind.id == kind_id)
        )
        entity = result.scalar_one_or_none()
        if not entity or entity.tenant_id != tenant_id:
            return False
        await self.db.delete(entity)
        await self.db.flush()
        return True
