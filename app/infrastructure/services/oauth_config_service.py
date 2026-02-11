"""OAuth config and flow service: authorize URL, callback exchange, create, rotate, update.

Encapsulates credential decryption, driver construction, state handling, and
encryption so API endpoints stay thin.
"""

from __future__ import annotations

from typing import Any

from app.infrastructure.external.email.envelope_encryption import OAuthStateManager
from app.infrastructure.external.email.oauth_drivers import (
    OAuthDriverRegistry,
    OAuthTokens,
)
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)
from app.infrastructure.persistence.repositories.oauth_state_repo import (
    OAuthStateRepository,
)


class OAuthConfigService:
    """Build OAuth URLs, exchange callback, create/rotate/update config with encryption."""

    def __init__(
        self,
        oauth_repo: OAuthProviderConfigRepository,
        state_repo: OAuthStateRepository,
        envelope_encryptor: Any,
        driver_registry: OAuthDriverRegistry,
    ) -> None:
        self._oauth_repo = oauth_repo
        self._state_repo = state_repo
        self._encryptor = envelope_encryptor
        self._driver_registry = driver_registry

    async def build_authorize_url(
        self,
        tenant_id: str,
        provider_type: str,
        user_id: str,
        return_url: str | None = None,
    ) -> str:
        """Return OAuth authorization URL for the provider. Raises ValueError if config missing or decrypt fails."""
        provider_type = provider_type.strip().lower()
        config = await self._oauth_repo.get_active_config(
            tenant_id=tenant_id, provider_type=provider_type
        )
        if not config:
            raise ValueError(f"No active OAuth config for provider: {provider_type}")
        _, signed_state = await self._state_repo.create_state(
            tenant_id=tenant_id,
            user_id=user_id,
            provider_config_id=config.id,
            return_url=return_url,
        )
        try:
            creds = self._encryptor.decrypt(config.client_id_encrypted)
        except ValueError:
            raise ValueError("Failed to decrypt OAuth credentials") from None
        if not isinstance(creds, dict):
            raise ValueError("Invalid credential format")
        client_id = creds.get("client_id", "")
        client_secret = creds.get("client_secret", "")
        scopes = config.default_scopes or config.allowed_scopes or []
        driver = self._driver_registry.get_driver(
            provider_type=provider_type,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=config.redirect_uri,
            scopes=scopes,
        )
        return driver.build_authorization_url(state=signed_state)

    async def exchange_callback(self, code: str, state: str) -> OAuthTokens:
        """Verify state, exchange code for tokens. Raises ValueError on invalid state or config."""
        state_manager = OAuthStateManager()
        try:
            state_id = state_manager.verify_and_extract(state)
        except ValueError:
            raise ValueError("Invalid or expired state") from None
        state_row = await self._state_repo.consume(state_id)
        if not state_row:
            raise ValueError("State already used or expired")
        config = await self._oauth_repo.get_by_id_and_tenant(
            state_row.provider_config_id, state_row.tenant_id or ""
        )
        if not config:
            raise ValueError("OAuth config not found")
        try:
            creds = self._encryptor.decrypt(config.client_id_encrypted)
        except ValueError:
            raise ValueError("Failed to decrypt OAuth credentials") from None
        if not isinstance(creds, dict):
            raise ValueError("Invalid credential format")
        client_id = creds.get("client_id", "")
        client_secret = creds.get("client_secret", "")
        scopes = config.default_scopes or config.allowed_scopes or []
        driver = self._driver_registry.get_driver(
            provider_type=config.provider_type,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=config.redirect_uri,
            scopes=scopes,
        )
        return await driver.exchange_code_for_tokens(code=code)

    async def create_config(
        self,
        tenant_id: str,
        provider_type: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
        created_by: str | None = None,
    ) -> Any:
        """Encrypt credentials and create new OAuth config version. Returns config."""
        envelope = self._encryptor.encrypt(
            {"client_id": client_id, "client_secret": client_secret}
        )
        key_id = self._encryptor.extract_key_id(envelope)
        return await self._oauth_repo.create_new_version(
            tenant_id=tenant_id,
            provider_type=provider_type.strip().lower(),
            client_id_encrypted=envelope,
            client_secret_encrypted=envelope,
            encryption_key_id=key_id,
            redirect_uri=redirect_uri.strip(),
            scopes=scopes or [],
            created_by=created_by,
        )

    async def rotate_config(
        self,
        config_id: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None,
        scopes: list[str] | None,
        updated_by: str | None = None,
    ) -> Any:
        """Load config, encrypt new credentials, create new version. Raises ValueError if config not found."""
        config = await self._oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
        if not config:
            raise ValueError("OAuth config not found")
        redirect_uri = redirect_uri or config.redirect_uri
        scopes = scopes or config.default_scopes or config.allowed_scopes or []
        envelope = self._encryptor.encrypt(
            {"client_id": client_id, "client_secret": client_secret}
        )
        key_id = self._encryptor.extract_key_id(envelope)
        return await self._oauth_repo.create_new_version(
            tenant_id=tenant_id,
            provider_type=config.provider_type,
            client_id_encrypted=envelope,
            client_secret_encrypted=envelope,
            encryption_key_id=key_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            display_name=config.display_name,
            created_by=updated_by,
        )

    async def update_config(
        self,
        config_id: str,
        tenant_id: str,
        *,
        display_name: str | None = None,
        redirect_uri: str | None = None,
        redirect_uri_whitelist: list[str] | None = None,
        allowed_scopes: list[str] | None = None,
        default_scopes: list[str] | None = None,
        tenant_configured_scopes: list[str] | None = None,
    ) -> Any:
        """Partially update config. Raises ValueError if config not found."""
        config = await self._oauth_repo.get_by_id_and_tenant(config_id, tenant_id)
        if not config:
            raise ValueError("OAuth config not found")
        if display_name is not None:
            config.display_name = display_name
        if redirect_uri is not None:
            config.redirect_uri = redirect_uri
        if redirect_uri_whitelist is not None:
            config.redirect_uri_whitelist = redirect_uri_whitelist
        if allowed_scopes is not None:
            config.allowed_scopes = allowed_scopes
        if default_scopes is not None:
            config.default_scopes = default_scopes
        if tenant_configured_scopes is not None:
            config.tenant_configured_scopes = tenant_configured_scopes
        await self._oauth_repo.update(config)
        return config
