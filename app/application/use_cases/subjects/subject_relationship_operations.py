"""Subject relationship operations: add, remove, list (delegate to ISubjectRelationshipRepository)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.event import EventCreate
from app.application.dtos.subject_relationship import SubjectRelationshipResult
from app.application.interfaces.repositories import (
    IRelationshipKindRepository,
    ISubjectRelationshipRepository,
    ISubjectRepository,
)
from app.application.services.relationship_event_schema import (
    RELATIONSHIP_ADDED_EVENT_TYPE,
    RELATIONSHIP_EVENT_SCHEMA_VERSION,
    RELATIONSHIP_REMOVED_EVENT_TYPE,
)
from app.domain.exceptions import ResourceNotFoundException, ValidationException
from app.shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.application.use_cases.events import EventService


class SubjectRelationshipService:
    """Add, remove, and list subject relationships (tenant-scoped)."""

    def __init__(
        self,
        relationship_repo: ISubjectRelationshipRepository,
        subject_repo: ISubjectRepository,
        event_service: "EventService | None" = None,
        relationship_kind_repo: IRelationshipKindRepository | None = None,
    ) -> None:
        self.relationship_repo = relationship_repo
        self.subject_repo = subject_repo
        self.event_service = event_service
        self.relationship_kind_repo = relationship_kind_repo

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
        await self._validate_relationship_kind(tenant_id, relationship_kind)
        result = await self.relationship_repo.create(
            tenant_id=tenant_id,
            source_subject_id=source_subject_id,
            target_subject_id=target_subject_id,
            relationship_kind=relationship_kind,
            payload=payload,
        )
        if self.event_service:
            await self._emit_relationship_event(
                tenant_id=tenant_id,
                subject_id=source_subject_id,
                event_type=RELATIONSHIP_ADDED_EVENT_TYPE,
                other_subject_id=target_subject_id,
                relationship_kind=relationship_kind,
            )
            await self._emit_relationship_event(
                tenant_id=tenant_id,
                subject_id=target_subject_id,
                event_type=RELATIONSHIP_ADDED_EVENT_TYPE,
                other_subject_id=source_subject_id,
                relationship_kind=relationship_kind,
            )
        return result

    async def remove_relationship(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
    ) -> bool:
        """Remove a relationship. Returns True if removed, False if not found."""
        deleted = await self.relationship_repo.delete(
            tenant_id=tenant_id,
            source_subject_id=source_subject_id,
            target_subject_id=target_subject_id,
            relationship_kind=relationship_kind,
        )
        if deleted and self.event_service:
            await self._emit_relationship_event(
                tenant_id=tenant_id,
                subject_id=source_subject_id,
                event_type=RELATIONSHIP_REMOVED_EVENT_TYPE,
                other_subject_id=target_subject_id,
                relationship_kind=relationship_kind,
            )
            await self._emit_relationship_event(
                tenant_id=tenant_id,
                subject_id=target_subject_id,
                event_type=RELATIONSHIP_REMOVED_EVENT_TYPE,
                other_subject_id=source_subject_id,
                relationship_kind=relationship_kind,
            )
        return deleted

    async def _validate_relationship_kind(
        self, tenant_id: str, relationship_kind: str
    ) -> None:
        """If tenant has configured relationship kinds, require relationship_kind to be one of them."""
        if not self.relationship_kind_repo:
            return
        kinds = await self.relationship_kind_repo.list_by_tenant(tenant_id)
        if not kinds:
            return
        allowed = {r.kind for r in kinds}
        if relationship_kind not in allowed:
            raise ValidationException(
                f"Relationship kind '{relationship_kind}' is not allowed for this tenant. "
                f"Allowed: {', '.join(sorted(allowed))}",
                field="relationship_kind",
            )

    async def _emit_relationship_event(
        self,
        tenant_id: str,
        subject_id: str,
        event_type: str,
        other_subject_id: str,
        relationship_kind: str,
    ) -> None:
        """Emit relationship_added or relationship_removed on one subject's timeline."""
        event_data = EventCreate(
            subject_id=subject_id,
            event_type=event_type,
            schema_version=RELATIONSHIP_EVENT_SCHEMA_VERSION,
            event_time=utc_now(),
            payload={
                "related_subject_id": other_subject_id,
                "relationship_kind": relationship_kind,
            },
        )
        await self.event_service.create_event(
            tenant_id=tenant_id,
            data=event_data,
            trigger_workflows=False,
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
