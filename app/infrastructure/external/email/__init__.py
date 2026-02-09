"""Email integration: protocols, factory, encryption, OAuth drivers, providers."""

from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import (
    EnvelopeEncryptor,
    OAuthStateManager,
)
from app.infrastructure.external.email.factory import EmailProviderFactory
from app.infrastructure.external.email.oauth_drivers import (
    GmailDriver,
    OAuthDriver,
    OAuthDriverRegistry,
    OAuthTokens,
    OAuthUserInfo,
    OutlookDriver,
    YahooDriver,
)
from app.infrastructure.external.email.protocols import (
    EmailMessage,
    EmailProviderConfig,
    IEmailProvider,
)

__all__ = [
    "CredentialEncryptor",
    "EmailMessage",
    "EmailProviderConfig",
    "EmailProviderFactory",
    "EnvelopeEncryptor",
    "GmailDriver",
    "IEmailProvider",
    "OAuthDriver",
    "OAuthDriverRegistry",
    "OAuthStateManager",
    "OAuthTokens",
    "OAuthUserInfo",
    "OutlookDriver",
    "YahooDriver",
]
