"""DocumentCategory repository with audit. Returns application DTOs. Tenant-scoped."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.document_category import DocumentCategoryResult
from app.domain.exceptions import ValidationException
from app.infrastructure.persistence.models.document_category import DocumentCategory
from app.infrastructure.persistence.repositories.auditable_repo import (
    TenantScopedRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _to_result(c: DocumentCategory) -> DocumentCategoryResult:
    """Map ORM DocumentCategory to DocumentCategoryResult."""
    return DocumentCategoryResult(
        id=c.id,
        tenant_id=c.tenant_id,
        category_name=c.category_name,
        display_name=c.display_name,
        description=c.description,
        metadata_schema=c.metadata_schema,
        default_retention_days=c.default_retention_days,
        is_active=c.is_active,
    )


class DocumentCategoryRepository(TenantScopedRepository[DocumentCategory]):
    """Document category configuration repository. All access scoped to a single tenant (tenant_id at construction)."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(
            db, DocumentCategory, tenant_id, audit_service, enable_audit=enable_audit
        )

    def _get_entity_type(self) -> str:
        return "document_category"

    def _serialize_for_audit(self, obj: DocumentCategory) -> dict[str, Any]:
        return {
            "id": obj.id,
            "category_name": obj.category_name,
            "display_name": obj.display_name,
            "is_active": obj.is_active,
        }

    async def get_by_id(self, category_id: str) -> DocumentCategoryResult | None:
        row = await super().get_by_id(category_id)
        return _to_result(row) if row else None

    async def get_by_tenant_and_name(
        self, tenant_id: str, category_name: str
    ) -> DocumentCategoryResult | None:
        if tenant_id != self._tenant_id:
            return None
        result = await self.db.execute(
            select(DocumentCategory).where(
                DocumentCategory.tenant_id == self._tenant_id,
                DocumentCategory.category_name == category_name,
                DocumentCategory.is_active.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[DocumentCategoryResult]:
        if tenant_id != self._tenant_id:
            return []
        result = await self.db.execute(
            select(DocumentCategory)
            .where(DocumentCategory.tenant_id == self._tenant_id)
            .order_by(DocumentCategory.category_name.asc())
            .offset(skip)
            .limit(limit)
        )
        return [_to_result(c) for c in result.scalars().all()]

    async def create_document_category(
        self,
        tenant_id: str,
        category_name: str,
        display_name: str,
        *,
        description: str | None = None,
        metadata_schema: dict | None = None,
        default_retention_days: int | None = None,
        is_active: bool = True,
    ) -> DocumentCategoryResult:
        if tenant_id != self._tenant_id:
            raise ValidationException(
                "Cannot create document category for another tenant",
                field="tenant_id",
            )
        entity = DocumentCategory(
            tenant_id=tenant_id,
            category_name=category_name,
            display_name=display_name,
            description=description,
            metadata_schema=metadata_schema,
            default_retention_days=default_retention_days,
            is_active=is_active,
        )
        created = await self.create(entity)
        return _to_result(created)

    async def update_document_category(
        self,
        category_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        metadata_schema: dict | None = None,
        default_retention_days: int | None = None,
        is_active: bool | None = None,
    ) -> DocumentCategoryResult | None:
        entity = await super().get_by_id(category_id)
        if not entity:
            return None
        if display_name is not None:
            entity.display_name = display_name
        if description is not None:
            entity.description = description
        if metadata_schema is not None:
            entity.metadata_schema = metadata_schema
        if default_retention_days is not None:
            entity.default_retention_days = default_retention_days
        if is_active is not None:
            entity.is_active = is_active
        updated = await self.update(entity, skip_existence_check=True)
        return _to_result(updated)

    async def delete_document_category(
        self, category_id: str, tenant_id: str
    ) -> bool:
        """Delete category by id. tenant_id must match repo scope (interface compatibility)."""
        if tenant_id != self._tenant_id:
            return False
        entity = await super().get_by_id(category_id)
        if not entity:
            return False
        await self.delete(entity)
        return True
