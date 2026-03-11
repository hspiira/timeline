"""Projection management use case: create, list, deactivate, rebuild (Phase 5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dtos.projection import ProjectionDefinitionResult

if TYPE_CHECKING:
    from app.application.interfaces.repositories import IProjectionRepository


class ProjectionManagementUseCase:
    """CRUD for projection definitions; engine picks up active definitions automatically."""

    def __init__(self, projection_repo: "IProjectionRepository") -> None:
        self._repo = projection_repo

    async def create_projection(
        self,
        tenant_id: str,
        name: str,
        version: int,
        subject_type: str | None = None,
    ) -> ProjectionDefinitionResult:
        """Create a projection definition (last_event_seq=0); engine will build it."""
        return await self._repo.create(
            tenant_id=tenant_id,
            name=name,
            version=version,
            subject_type=subject_type,
        )

    async def list_projections(
        self, tenant_id: str
    ) -> list[ProjectionDefinitionResult]:
        """List all projection definitions for the tenant (active and inactive)."""
        return await self._repo.list_by_tenant(tenant_id=tenant_id)

    async def deactivate_projection(
        self, tenant_id: str, name: str, version: int
    ) -> None:
        """Set active=False; engine will skip this projection."""
        await self._repo.deactivate(tenant_id=tenant_id, name=name, version=version)

    async def rebuild_projection(
        self, tenant_id: str, name: str, version: int
    ) -> None:
        """Reset last_event_seq=0; engine will replay from genesis on next cycle."""
        await self._repo.reset_watermark(
            tenant_id=tenant_id, name=name, version=version
        )
