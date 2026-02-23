"""Email provider factory: creates Gmail, IMAP, or Outlook provider from config."""

from typing import ClassVar

import httpx

from app.infrastructure.external.email.protocols import (
    EmailProviderConfig,
    IEmailProvider,
)
from app.infrastructure.external.email.providers.gmail_provider import GmailProvider
from app.infrastructure.external.email.providers.imap_provider import IMAPProvider
from app.infrastructure.external.email.providers.outlook_provider import OutlookProvider
from app.shared.telemetry.logging import get_logger

logger = get_logger(__name__)


class EmailProviderFactory:
    """Factory for email provider instances by provider_type."""

    _providers: ClassVar[dict[str, type[IEmailProvider]]] = {
        "gmail": GmailProvider,
        "outlook": OutlookProvider,
        "imap": IMAPProvider,
        "icloud": IMAPProvider,
        "yahoo": IMAPProvider,
    }

    @classmethod
    def create_provider(
        cls,
        config: EmailProviderConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> IEmailProvider:
        """Create provider instance for config.

        Args:
            config: Email provider configuration.
            http_client: Optional shared httpx.AsyncClient for connection reuse
                (e.g. OutlookProvider uses it for Graph API calls).

        Returns:
            GmailProvider, IMAPProvider, or OutlookProvider.

        Raises:
            ValueError: If provider_type not supported.
        """
        provider_type = config.provider_type.lower()
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            raise ValueError(
                f"Unsupported provider: {config.provider_type}. "
                f"Supported: {list(cls._providers.keys())}"
            )
        logger.debug("Creating %s for %s", provider_class.__name__, config.email_address)
        if provider_class.__name__ == "OutlookProvider" and http_client is not None:
            return provider_class(http_client=http_client)
        return provider_class()

    @classmethod
    def register_provider(
        cls,
        provider_type: str,
        provider_class: type[IEmailProvider],
    ) -> None:
        """Register a custom provider type."""
        cls._providers[provider_type.lower()] = provider_class
        logger.info("Registered custom provider: %s", provider_type)

    @classmethod
    def list_supported_providers(cls) -> list[str]:
        """Return list of supported provider types."""
        return list(cls._providers.keys())
