"""Subject relationship operations: add, remove, list (delegate to ISubjectRelationshipRepository)."""

from __future__ import annotations

from app.application.dtos.subject_relationship import SubjectRelationshipResult
from app.application.interfaces.repositories import (
    ISubjectRelationshipRepository,
    ISubjectRepository,
)
from app.domain.exceptions import ResourceNotFoundException


class SubjectRelationshipService:
    """Add, remove, and list subject relationships (tenant-scoped)."""

    def __init__(
        self,
        relationship_repo: ISubjectRelationshipRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self.relationship_repo = relationship_repo
        self.subject_repo = subject_repo

    async def add_relationship(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
        payload: dict | None = None,
    ) -> SubjectRelationshipResult:
        """Add a relationship from source to target. Validates both subjects exist in tenant."""
        await self._ensure_subject_in_tenant(tenant_id, source_subject_id, "source_subject_id")
        await self._ensure_subject_in_tenant(tenant_id, target_subject_id, "target_subject_id")
        return await self.relationship_repo.create(
            tenant_id=tenant_id,
            source_subject_id=source_subject_id,
            target_subject_id=target_subject_id,
            relationship_kind=relationship_kind,
            payload=payload,
        )

    async def remove_relationship(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
    ) -> bool:
        """Remove a relationship. Returns True if removed, False if not found."""
        return await self.relationship_repo.delete(
            tenant_id=tenant_id,
            source_subject_id=source_subject_id,
            target_subject_id=target_subject_id,
            relationship_kind=relationship_kind,
        )

    async def list_relationships(
        self,
        tenant_id: str,
        subject_id: str,
        *,
        as_source: bool = True,
        as_target: bool = True,
        relationship_kind: str | None = None,
    ) -> list[SubjectRelationshipResult]:
        """List relationships for a subject. Ensures subject exists in tenant."""
        await self._ensure_subject_in_tenant(tenant_id, subject_id, "subject_id")
        return await self.relationship_repo.list_for_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
            as_source=as_source,
            as_target=as_target,
            relationship_kind=relationship_kind,
        )

    async def _ensure_subject_in_tenant(
        self, tenant_id: str, subject_id: str, field: str
    ) -> None:
        """Raise ResourceNotFoundException if subject not found in tenant."""
        subject = await self.subject_repo.get_by_id_and_tenant(subject_id, tenant_id)
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)
