"""SubjectType repository with audit. Returns application DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.subject_type import SubjectTypeResult
from app.infrastructure.persistence.models.subject_type import SubjectType
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _to_result(s: SubjectType) -> SubjectTypeResult:
    """Map ORM SubjectType to SubjectTypeResult."""
    return SubjectTypeResult(
        id=s.id,
        tenant_id=s.tenant_id,
        type_name=s.type_name,
        display_name=s.display_name,
        description=s.description,
        schema=s.schema,
        version=s.version,
        is_active=s.is_active,
        icon=s.icon,
        color=s.color,
        has_timeline=s.has_timeline,
        allow_documents=s.allow_documents,
        created_by=s.created_by,
    )


class SubjectTypeRepository(AuditableRepository[SubjectType]):
    """Subject type configuration repository. Tenant-scoped via method args."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, SubjectType, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "subject_type"

    def _serialize_for_audit(self, obj: SubjectType) -> dict[str, Any]:
        return {
            "id": obj.id,
            "type_name": obj.type_name,
            "display_name": obj.display_name,
            "version": obj.version,
            "is_active": obj.is_active,
        }

    async def get_by_id(self, subject_type_id: str) -> SubjectTypeResult | None:
        row = await super().get_by_id(subject_type_id)
        return _to_result(row) if row else None

    async def get_by_tenant_and_type(
        self, tenant_id: str, type_name: str
    ) -> SubjectTypeResult | None:
        result = await self.db.execute(
            select(SubjectType).where(
                SubjectType.tenant_id == tenant_id,
                SubjectType.type_name == type_name,
                SubjectType.is_active.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        return _to_result(row) if row else None

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[SubjectTypeResult]:
        result = await self.db.execute(
            select(SubjectType)
            .where(SubjectType.tenant_id == tenant_id)
            .order_by(SubjectType.type_name.asc())
            .offset(skip)
            .limit(limit)
        )
        return [_to_result(s) for s in result.scalars().all()]

    async def create_subject_type(
        self,
        tenant_id: str,
        type_name: str,
        display_name: str,
        *,
        description: str | None = None,
        schema: dict | None = None,
        is_active: bool = True,
        icon: str | None = None,
        color: str | None = None,
        has_timeline: bool = True,
        allow_documents: bool = True,
        created_by: str | None = None,
    ) -> SubjectTypeResult:
        entity = SubjectType(
            tenant_id=tenant_id,
            type_name=type_name,
            display_name=display_name,
            description=description,
            schema=schema,
            version=1,
            is_active=is_active,
            icon=icon,
            color=color,
            has_timeline=has_timeline,
            allow_documents=allow_documents,
            created_by=created_by,
        )
        created = await self.create(entity)
        return _to_result(created)

    async def update_subject_type(
        self,
        subject_type_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        schema: dict | None = None,
        is_active: bool | None = None,
        icon: str | None = None,
        color: str | None = None,
        has_timeline: bool | None = None,
        allow_documents: bool | None = None,
    ) -> SubjectTypeResult | None:
        entity = await super().get_by_id(subject_type_id)
        if not entity:
            return None
        if display_name is not None:
            entity.display_name = display_name
        if description is not None:
            entity.description = description
        if schema is not None:
            entity.schema = schema
        if is_active is not None:
            entity.is_active = is_active
        if icon is not None:
            entity.icon = icon
        if color is not None:
            entity.color = color
        if has_timeline is not None:
            entity.has_timeline = has_timeline
        if allow_documents is not None:
            entity.allow_documents = allow_documents
        updated = await self.update(entity, skip_existence_check=True)
        return _to_result(updated)

    async def delete_subject_type(
        self, subject_type_id: str, tenant_id: str
    ) -> bool:
        entity = await super().get_by_id(subject_type_id)
        if not entity or entity.tenant_id != tenant_id:
            return False
        await self.delete(entity)
        return True
