"""Subject operations: create, get, list (delegate to ISubjectRepository)."""

from __future__ import annotations

from app.application.dtos.subject import SubjectResult
from app.application.interfaces.repositories import ISubjectRepository
from app.domain.exceptions import ResourceNotFoundException, ValidationException
from app.domain.value_objects.core import SubjectType


class SubjectService:
    """Create and query subjects (tenant-scoped). Validates subject type and external_ref uniqueness."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self.subject_repo = subject_repo

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
    ) -> SubjectResult:
        """Create a subject; validate subject_type and enforce unique external_ref per tenant."""
        try:
            st = SubjectType(subject_type)
        except ValueError as e:
            raise ValidationException(str(e), field="subject_type") from e

        if external_ref and external_ref.strip():
            existing = await self.subject_repo.get_by_external_ref(
                tenant_id, external_ref.strip()
            )
            if existing:
                raise ValidationException(
                    "Subject with this external reference already exists for this tenant",
                    field="external_ref",
                )

        ref = (external_ref.strip() or None) if external_ref else None
        return await self.subject_repo.create_subject(
            tenant_id=tenant_id,
            subject_type=st.value,
            external_ref=ref,
        )

    async def get_subject(self, tenant_id: str, subject_id: str) -> SubjectResult:
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
    ) -> list[SubjectResult]:
        """Return subjects for tenant with optional type filter."""
        if subject_type:
            try:
                st = SubjectType(subject_type)
            except ValueError as e:
                raise ValidationException(str(e), field="subject_type") from e
            return await self.subject_repo.get_by_type(
                tenant_id=tenant_id,
                subject_type=st.value,
                skip=skip,
                limit=limit,
            )
        return await self.subject_repo.get_by_tenant(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
        )

    async def update_subject(
        self,
        tenant_id: str,
        subject_id: str,
        external_ref: str | None = None,
    ) -> SubjectResult:
        """Update subject; raise ResourceNotFoundException if not found in tenant."""
        result = await self.subject_repo.update_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
            external_ref=external_ref,
        )
        if result is None:
            raise ResourceNotFoundException("subject", subject_id)
        return result

    async def delete_subject(self, tenant_id: str, subject_id: str) -> None:
        """Delete subject; raise ResourceNotFoundException if not found in tenant."""
        deleted = await self.subject_repo.delete_subject(
            tenant_id=tenant_id,
            subject_id=subject_id,
        )
        if not deleted:
            raise ResourceNotFoundException("subject", subject_id)
