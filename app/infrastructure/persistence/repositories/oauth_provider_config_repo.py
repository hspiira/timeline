"""OAuth provider config repository with versioning and list."""

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
from app.shared.enums import AuditAction
from app.shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.infrastructure.services.system_audit_service import SystemAuditService


def _display_name(provider_type: str) -> str:
    names = {"gmail": "Gmail", "outlook": "Microsoft 365", "yahoo": "Yahoo Mail"}
    return names.get(provider_type, provider_type.title())


def _auth_endpoint(provider_type: str) -> str:
    endpoints = {
        "gmail": "https://accounts.google.com/o/oauth2/v2/auth",
        "outlook": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "yahoo": "https://api.login.yahoo.com/oauth2/request_auth",
    }
    endpoint = endpoints.get(provider_type)
    if not endpoint:
        raise ValueError(f"Unsupported OAuth provider type: {provider_type}")
    return endpoint


def _token_endpoint(provider_type: str) -> str:
    endpoints = {
        "gmail": "https://oauth2.googleapis.com/token",
        "outlook": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "yahoo": "https://api.login.yahoo.com/oauth2/get_token",
    }
    endpoint = endpoints.get(provider_type)
    if not endpoint:
        raise ValueError(f"Unsupported OAuth provider type: {provider_type}")
    return endpoint


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
        """Return OAuth provider config by id if it belongs to tenant (excludes soft-deleted)."""
        result = await self.db.execute(
            select(OAuthProviderConfig).where(
                OAuthProviderConfig.id == config_id,
                OAuthProviderConfig.tenant_id == tenant_id,
                OAuthProviderConfig.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_configs(
        self,
        tenant_id: str,
        include_inactive: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OAuthProviderConfig]:
        """List OAuth provider configs for tenant."""
        q = select(OAuthProviderConfig).where(
            OAuthProviderConfig.tenant_id == tenant_id,
            OAuthProviderConfig.deleted_at.is_(None),
        )
        if not include_inactive:
            q = q.where(OAuthProviderConfig.is_active.is_(True))
        q = q.order_by(
            OAuthProviderConfig.provider_type.asc(),
            OAuthProviderConfig.version.desc(),
        ).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create_new_version(
        self,
        tenant_id: str,
        provider_type: str,
        client_id_encrypted: str,
        client_secret_encrypted: str,
        encryption_key_id: str,
        redirect_uri: str,
        scopes: list[str],
        display_name: str | None = None,
        created_by: str | None = None,
    ) -> OAuthProviderConfig:
        """Create first or new version of OAuth config. Deactivates previous active if any."""
        current = await self.get_active_config(tenant_id, provider_type)
        if current:
            new_version = current.version + 1
            new_config = OAuthProviderConfig(
                tenant_id=tenant_id,
                provider_type=provider_type,
                display_name=display_name or current.display_name,
                version=new_version,
                is_active=True,
                client_id_encrypted=client_id_encrypted,
                client_secret_encrypted=client_secret_encrypted,
                encryption_key_id=encryption_key_id,
                redirect_uri=redirect_uri,
                redirect_uri_whitelist=current.redirect_uri_whitelist or [redirect_uri],
                allowed_scopes=scopes,
                default_scopes=scopes,
                tenant_configured_scopes=scopes,
                authorization_endpoint=current.authorization_endpoint,
                token_endpoint=current.token_endpoint,
                provider_metadata=current.provider_metadata,
                created_by=created_by,
            )
        else:
            new_config = OAuthProviderConfig(
                tenant_id=tenant_id,
                provider_type=provider_type,
                display_name=display_name or _display_name(provider_type),
                version=1,
                is_active=True,
                client_id_encrypted=client_id_encrypted,
                client_secret_encrypted=client_secret_encrypted,
                encryption_key_id=encryption_key_id,
                redirect_uri=redirect_uri,
                redirect_uri_whitelist=[redirect_uri],
                allowed_scopes=scopes,
                default_scopes=scopes,
                tenant_configured_scopes=scopes,
                authorization_endpoint=_auth_endpoint(provider_type),
                token_endpoint=_token_endpoint(provider_type),
                created_by=created_by,
            )
        await self.create(new_config)
        if current:
            current.is_active = False
            current.superseded_by_id = new_config.id
            await self.update(current)
            await self.emit_custom_audit(
                new_config,
                AuditAction.STATUS_CHANGED,
                metadata={
                    "operation": "credential_rotation",
                    "previous_version": current.version,
                    "new_version": new_config.version,
                },
            )
        return new_config

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

    async def soft_delete(
        self, config_id: str, tenant_id: str, deleted_by: str | None = None
    ) -> OAuthProviderConfig | None:
        """Soft-delete config (set deleted_at). Returns updated config or None."""
        config = await self.get_by_id_and_tenant(config_id, tenant_id)
        if not config:
            return None
        config.deleted_at = utc_now()
        if deleted_by is not None and hasattr(config, "deleted_by"):
            config.deleted_by = deleted_by
        await self.update(config)
        return config
