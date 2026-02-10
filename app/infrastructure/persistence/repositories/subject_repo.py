"""Subject repository with audit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.subject import Subject
from app.infrastructure.persistence.repositories.auditable_repo import AuditableRepository

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class SubjectRepository(AuditableRepository[Subject]):
    """Subject repository."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(db, Subject, audit_service, enable_audit=enable_audit)

    def _get_entity_type(self) -> str:
        return "subject"

    def _get_tenant_id(self, obj: Subject) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: Subject) -> dict[str, Any]:
        return {
            "id": obj.id,
            "subject_type": obj.subject_type,
            "external_ref": obj.external_ref,
        }

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[Subject]:
        result = await self.db.execute(
            select(Subject).where(Subject.tenant_id == tenant_id).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        tenant_id: str,
        subject_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Subject]:
        result = await self.db.execute(
            select(Subject)
            .where(
                Subject.tenant_id == tenant_id,
                Subject.subject_type == subject_type,
            )
            .order_by(Subject.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_external_ref(
        self, tenant_id: str, external_ref: str
    ) -> Subject | None:
        result = await self.db.execute(
            select(Subject).where(
                Subject.tenant_id == tenant_id,
                Subject.external_ref == external_ref,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_tenant(self, subject_id: str, tenant_id: str) -> Subject | None:
        result = await self.db.execute(
            select(Subject).where(
                Subject.id == subject_id,
                Subject.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
    ) -> Subject:
        """Create subject; return created entity."""
        subject = Subject(
            tenant_id=tenant_id,
            subject_type=subject_type,
            external_ref=external_ref,
        )
        return await self.create(subject)
