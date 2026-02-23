"""Subject repository with audit. Returns application DTOs. Tenant-scoped."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.subject import SubjectResult
from app.domain.exceptions import ValidationException
from app.domain.value_objects.core import SubjectType
from app.infrastructure.persistence.models.subject import Subject
from app.infrastructure.persistence.repositories.auditable_repo import (
    TenantScopedRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _subject_to_result(s: Subject) -> SubjectResult:
    """Map ORM Subject to application SubjectResult."""
    return SubjectResult(
        id=s.id,
        tenant_id=s.tenant_id,
        subject_type=SubjectType(s.subject_type),
        external_ref=s.external_ref,
        display_name=s.display_name or s.external_ref or "",
        attributes=s.attributes if s.attributes is not None else {},
    )


class SubjectRepository(TenantScopedRepository[Subject]):
    """Subject repository. All access scoped to a single tenant (tenant_id at construction)."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Subject, tenant_id, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "subject"

    def _serialize_for_audit(self, obj: Subject) -> dict[str, Any]:
        return {
            "id": obj.id,
            "subject_type": obj.subject_type,
            "external_ref": obj.external_ref,
            "display_name": obj.display_name,
            "attributes": obj.attributes,
        }

    async def get_entity_by_id_and_tenant(
        self, subject_id: str, tenant_id: str
    ) -> Subject | None:
        """Get subject ORM by id and tenant for update/delete. Asserts tenant matches scope."""
        if tenant_id != self._tenant_id:
            return None
        return await super().get_by_id(subject_id)

    async def get_by_id(self, subject_id: str) -> SubjectResult | None:
        orm = await super().get_by_id(subject_id)
        return _subject_to_result(orm) if orm else None

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return total subject count for tenant."""
        if tenant_id != self._tenant_id:
            return 0
        result = await self.db.execute(
            select(func.count(Subject.id)).where(Subject.tenant_id == self._tenant_id)
        )
        return result.scalar() or 0

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[SubjectResult]:
        if tenant_id != self._tenant_id:
            return []
        result = await self.db.execute(
            select(Subject)
            .where(Subject.tenant_id == self._tenant_id)
            .order_by(Subject.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [_subject_to_result(s) for s in result.scalars().all()]

    async def get_counts_by_type(self, tenant_id: str) -> dict[str, int]:
        """Return subject counts per subject_type for tenant."""
        if tenant_id != self._tenant_id:
            return {}
        result = await self.db.execute(
            select(Subject.subject_type, func.count(Subject.id))
            .where(Subject.tenant_id == self._tenant_id)
            .group_by(Subject.subject_type)
        )
        return dict(result.all())

    async def get_by_type(
        self,
        tenant_id: str,
        subject_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SubjectResult]:
        if tenant_id != self._tenant_id:
            return []
        result = await self.db.execute(
            select(Subject)
            .where(
                Subject.tenant_id == self._tenant_id,
                Subject.subject_type == subject_type,
            )
            .order_by(Subject.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [_subject_to_result(s) for s in result.scalars().all()]

    async def get_by_external_ref(
        self, tenant_id: str, external_ref: str
    ) -> SubjectResult | None:
        if tenant_id != self._tenant_id:
            return None
        result = await self.db.execute(
            select(Subject).where(
                Subject.tenant_id == self._tenant_id,
                Subject.external_ref == external_ref,
            )
        )
        row = result.scalar_one_or_none()
        return _subject_to_result(row) if row else None

    async def get_by_id_and_tenant(
        self, subject_id: str, tenant_id: str
    ) -> SubjectResult | None:
        if tenant_id != self._tenant_id:
            return None
        return await self.get_by_id(subject_id)

    async def get_by_ids_and_tenant(
        self, tenant_id: str, subject_ids: set[str]
    ) -> list[SubjectResult]:
        """Return subjects for the given ids in this tenant (batch; one query)."""
        if tenant_id != self._tenant_id or not subject_ids:
            return []
        result = await self.db.execute(
            select(Subject).where(
                Subject.tenant_id == self._tenant_id,
                Subject.id.in_(subject_ids),
            )
        )
        return [_subject_to_result(s) for s in result.scalars().all()]

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
        display_name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> SubjectResult:
        """Create subject; return created entity. Asserts tenant_id matches scope."""
        if tenant_id != self._tenant_id:
            raise ValidationException(
                "Cannot create subject for another tenant",
                field="tenant_id",
            )
        resolved_display_name = display_name if display_name is not None else (external_ref or "")
        subject = Subject(
            tenant_id=self._tenant_id,
            subject_type=subject_type,
            external_ref=external_ref,
            display_name=resolved_display_name or None,
            attributes=attributes if attributes is not None else {},
        )
        created = await self.create(subject)
        return _subject_to_result(created)

    async def update_subject(
        self,
        tenant_id: str,
        subject_id: str,
        external_ref: str | None = None,
        display_name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> SubjectResult | None:
        """Update subject; return updated result or None if not found in tenant."""
        entity = await self.get_entity_by_id_and_tenant(subject_id, tenant_id)
        if not entity:
            return None
        if external_ref is not None:
            entity.external_ref = external_ref
        if display_name is not None:
            entity.display_name = display_name
        if attributes is not None:
            entity.attributes = attributes
        updated = await self.update(entity, skip_existence_check=True)
        return _subject_to_result(updated)

    async def delete_subject(self, tenant_id: str, subject_id: str) -> bool:
        """Delete subject; return True if deleted, False if not found in tenant."""
        entity = await self.get_entity_by_id_and_tenant(subject_id, tenant_id)
        if not entity:
            return False
        await self.delete(entity)
        return True
