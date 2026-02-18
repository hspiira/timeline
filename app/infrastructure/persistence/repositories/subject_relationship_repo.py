"""Subject relationship repository. Tenant-scoped."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.subject_relationship import SubjectRelationshipResult
from app.domain.exceptions import ValidationException
from app.infrastructure.persistence.models.subject import Subject
from app.infrastructure.persistence.models.subject_relationship import (
    SubjectRelationship,
)
from app.infrastructure.persistence.repositories.auditable_repo import (
    TenantScopedRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _to_result(r: SubjectRelationship) -> SubjectRelationshipResult:
    """Map ORM to SubjectRelationshipResult."""
    return SubjectRelationshipResult(
        id=r.id,
        tenant_id=r.tenant_id,
        source_subject_id=r.source_subject_id,
        target_subject_id=r.target_subject_id,
        relationship_kind=r.relationship_kind,
        payload=r.payload,
        created_at=r.created_at,
    )


class SubjectRelationshipRepository(TenantScopedRepository[SubjectRelationship]):
    """Subject relationship repository. All access scoped to a single tenant."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        audit_service: "SystemAuditService | None" = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(
            db, SubjectRelationship, tenant_id, audit_service, enable_audit=enable_audit
        )

    def _get_entity_type(self) -> str:
        return "subject_relationship"

    def _serialize_for_audit(self, obj: SubjectRelationship) -> dict[str, Any]:
        return {
            "id": obj.id,
            "source_subject_id": obj.source_subject_id,
            "target_subject_id": obj.target_subject_id,
            "relationship_kind": obj.relationship_kind,
        }

    async def create(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
        payload: dict | None = None,
    ) -> SubjectRelationshipResult:
        """Create a relationship. Ensures both subjects exist in tenant."""
        if tenant_id != self._tenant_id:
            raise ValidationException(
                "Cannot create relationship for another tenant",
                field="tenant_id",
            )
        # Ensure both subjects exist and belong to tenant
        for sid, label in [
            (source_subject_id, "source_subject_id"),
            (target_subject_id, "target_subject_id"),
        ]:
            result = await self.db.execute(
                select(Subject).where(
                    Subject.id == sid,
                    Subject.tenant_id == self._tenant_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise ValidationException(
                    f"Subject {label} does not exist or does not belong to tenant",
                    field=label,
                )
        if source_subject_id == target_subject_id:
            raise ValidationException(
                "Source and target subject must be different",
                field="target_subject_id",
            )
        rel = SubjectRelationship(
            tenant_id=self._tenant_id,
            source_subject_id=source_subject_id,
            target_subject_id=target_subject_id,
            relationship_kind=relationship_kind,
            payload=payload,
        )
        created = await super().create(rel)
        return _to_result(created)

    async def delete(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
    ) -> bool:
        """Delete relationship; return True if deleted."""
        if tenant_id != self._tenant_id:
            return False
        result = await self.db.execute(
            select(SubjectRelationship).where(
                SubjectRelationship.tenant_id == self._tenant_id,
                SubjectRelationship.source_subject_id == source_subject_id,
                SubjectRelationship.target_subject_id == target_subject_id,
                SubjectRelationship.relationship_kind == relationship_kind,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await super().delete(row)
        return True

    async def list_for_subject(
        self,
        tenant_id: str,
        subject_id: str,
        *,
        as_source: bool = True,
        as_target: bool = True,
        relationship_kind: str | None = None,
    ) -> list[SubjectRelationshipResult]:
        """List relationships where subject is source and/or target."""
        if tenant_id != self._tenant_id:
            return []
        q = select(SubjectRelationship).where(
            SubjectRelationship.tenant_id == self._tenant_id,
        )
        if as_source and as_target:
            from sqlalchemy import or_

            q = q.where(
                or_(
                    SubjectRelationship.source_subject_id == subject_id,
                    SubjectRelationship.target_subject_id == subject_id,
                )
            )
        elif as_source:
            q = q.where(SubjectRelationship.source_subject_id == subject_id)
        elif as_target:
            q = q.where(SubjectRelationship.target_subject_id == subject_id)
        else:
            return []
        if relationship_kind is not None:
            q = q.where(SubjectRelationship.relationship_kind == relationship_kind)
        q = q.order_by(SubjectRelationship.created_at.desc())
        result = await self.db.execute(q)
        return [_to_result(r) for r in result.scalars().all()]