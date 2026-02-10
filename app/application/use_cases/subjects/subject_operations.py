"""Subject operations: create, get, list (delegate to ISubjectRepository)."""

from __future__ import annotations

from typing import Any

from app.application.interfaces.repositories import ISubjectRepository
from app.domain.exceptions import ResourceNotFoundException


class SubjectService:
    """Create and query subjects (tenant-scoped)."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self.subject_repo = subject_repo

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
    ) -> Any:
        """Create a subject; return created entity."""
        return await self.subject_repo.create_subject(
            tenant_id=tenant_id,
            subject_type=subject_type,
            external_ref=external_ref,
        )

    async def get_subject(
        self, tenant_id: str, subject_id: str
    ) -> Any:
        """Return subject by id if it belongs to tenant; else raise ResourceNotFoundException."""
        subject = await self.subject_repo.get_by_id_and_tenant(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )
        if not subject:
            raise ResourceNotFoundException("subject", subject_id)
        return subject

    async def list_subjects(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        subject_type: str | None = None,
    ) -> list[Any]:
        """Return subjects for tenant with optional type filter."""
        if subject_type:
            return await self.subject_repo.get_by_type(
                tenant_id=tenant_id,
                subject_type=subject_type,
                skip=skip,
                limit=limit,
            )
        return await self.subject_repo.get_by_tenant(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
        )
