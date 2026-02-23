"""Auth and token dependencies (composition root)."""

from __future__ import annotations

from fastapi import Request

from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import (
    EnvelopeEncryptor, OAuthStateManager)
from app.infrastructure.external.email.oauth_drivers import OAuthDriverRegistry
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.password import get_password_hash


class AuthSecurity:
    """Token and password hashing provided via DI (no direct infra imports in routes)."""

    def create_access_token(self, data: dict) -> str:
        """Build a JWT access token from the given payload.

        Args:
            data: Claim payload (e.g. sub, tenant_id, exp). Passed to JWT encoder.

        Returns:
            Encoded JWT string.
        """
        return create_access_token(data)

    def hash_password(self, password: str) -> str:
        """Hash a plain-text password for storage.

        Args:
            password: Plain-text password to hash.

        Returns:
            Bcrypt-hashed password string.
        """
        return get_password_hash(password)


def get_auth_security() -> AuthSecurity:
    """Auth token creation and password hashing dependency.

    Returns:
        AuthSecurity instance for create_access_token and hash_password.
    """
    return AuthSecurity()


def get_credential_encryptor() -> CredentialEncryptor:
    """Credential encryptor for email account credentials.

    Returns:
        CredentialEncryptor instance for encrypting/decrypting stored credentials.
    """
    return CredentialEncryptor()


def get_envelope_encryptor() -> EnvelopeEncryptor:
    """Envelope encryptor for OAuth client secrets.

    Returns:
        EnvelopeEncryptor instance for encrypting/decrypting OAuth secrets.
    """
    return EnvelopeEncryptor()


def get_oauth_state_manager() -> OAuthStateManager:
    """OAuth state signing and verification for authorize/callback flows.

    Returns:
        OAuthStateManager instance for signing and verifying state parameters.
    """
    return OAuthStateManager()


def get_oauth_driver_registry(request: Request) -> OAuthDriverRegistry:
    """OAuth driver registry with shared HTTP client from app state.

    Args:
        request: Incoming request; app.state.oauth_http_client is used when set.

    Returns:
        OAuthDriverRegistry configured with the shared HTTP client.
    """
    http_client = getattr(request.app.state, "oauth_http_client", None)
    return OAuthDriverRegistry(http_client=http_client)
