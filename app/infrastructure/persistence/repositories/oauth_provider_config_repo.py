"""OAuth provider config repository (minimal for Phase 3)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.oauth_provider_config import (
    OAuthProviderConfig,
)
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


class OAuthProviderConfigRepository(AuditableRepository[OAuthProviderConfig]):
    """OAuth provider config repository."""

    def __init__(
        self,
        db: AsyncSession,
        audit_service: SystemAuditService | None = None,
        *,
        enable_audit: bool = True,
    ) -> None:
        super().__init__(
            db, OAuthProviderConfig, audit_service, enable_audit=enable_audit
        )

    def _get_entity_type(self) -> str:
        return "oauth_provider"

    def _get_tenant_id(self, obj: OAuthProviderConfig) -> str:
        return obj.tenant_id

    def _serialize_for_audit(self, obj: OAuthProviderConfig) -> dict[str, Any]:
        return {
            "id": obj.id,
            "provider_type": obj.provider_type,
            "display_name": obj.display_name,
            "version": obj.version,
            "is_active": obj.is_active,
            "health_status": obj.health_status,
        }

    async def get_by_id_and_tenant(
        self, config_id: str, tenant_id: str
    ) -> OAuthProviderConfig | None:
        """Return OAuth provider config by id if it belongs to tenant."""
        result = await self.db.execute(
            select(OAuthProviderConfig).where(
                OAuthProviderConfig.id == config_id,
                OAuthProviderConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_config(
        self, tenant_id: str, provider_type: str
    ) -> OAuthProviderConfig | None:
        result = await self.db.execute(
            select(OAuthProviderConfig).where(
                and_(
                    OAuthProviderConfig.tenant_id == tenant_id,
                    OAuthProviderConfig.provider_type == provider_type,
                    OAuthProviderConfig.is_active.is_(True),
                    OAuthProviderConfig.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_config_by_version(
        self, tenant_id: str, provider_type: str, version: int
    ) -> OAuthProviderConfig | None:
        result = await self.db.execute(
            select(OAuthProviderConfig).where(
                and_(
                    OAuthProviderConfig.tenant_id == tenant_id,
                    OAuthProviderConfig.provider_type == provider_type,
                    OAuthProviderConfig.version == version,
                    OAuthProviderConfig.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()
