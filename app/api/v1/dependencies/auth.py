"""Auth and token dependencies (composition root)."""

from __future__ import annotations

from fastapi import Request

from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import (
    EnvelopeEncryptor,
    OAuthStateManager,
)
from app.infrastructure.external.email.oauth_drivers import OAuthDriverRegistry
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.password import get_password_hash


class AuthSecurity:
    """Token and password hashing provided via DI (no direct infra imports in routes)."""

    def create_access_token(self, data: dict) -> str:
        return create_access_token(data)

    def hash_password(self, password: str) -> str:
        return get_password_hash(password)


def get_auth_security() -> AuthSecurity:
    """Auth token creation and password hashing (composition root)."""
    return AuthSecurity()


def get_credential_encryptor() -> CredentialEncryptor:
    """Credential encryptor for email accounts (composition root)."""
    return CredentialEncryptor()


def get_envelope_encryptor() -> EnvelopeEncryptor:
    """Envelope encryptor for OAuth client secrets (composition root)."""
    return EnvelopeEncryptor()


def get_oauth_state_manager() -> OAuthStateManager:
    """OAuth state signing/verification (composition root)."""
    return OAuthStateManager()


def get_oauth_driver_registry(request: Request) -> OAuthDriverRegistry:
    """OAuth driver registry with shared HTTP client (composition root)."""
    http_client = getattr(request.app.state, "oauth_http_client", None)
    return OAuthDriverRegistry(http_client=http_client)
