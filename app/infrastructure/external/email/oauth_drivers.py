"""OAuth provider drivers: authorization URL, token exchange, refresh, user info."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx

from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass
class OAuthTokens:
    """Normalized OAuth token response."""

    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int
    expires_at: datetime
    scope: str
    provider_metadata: dict[str, Any] | None = None


@dataclass
class OAuthUserInfo:
    """Normalized user info from provider."""

    email: str
    name: str | None = None
    picture: str | None = None
    provider_user_id: str | None = None
    provider_metadata: dict[str, Any] | None = None


class OAuthDriver(ABC):
    """Abstract OAuth driver: auth URL, token exchange, refresh, user info."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes

    PROVIDER_NAME: ClassVar[str]
    PROVIDER_TYPE: ClassVar[str]
    AUTHORIZATION_ENDPOINT: ClassVar[str]
    TOKEN_ENDPOINT: ClassVar[str]
    SUPPORTS_PKCE: ClassVar[bool] = False
    _SENSITIVE_KEYS: ClassVar[frozenset[str]] = frozenset(
        {"access_token", "refresh_token", "id_token"}
    )

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    @property
    def provider_type(self) -> str:
        return self.PROVIDER_TYPE

    @property
    def authorization_endpoint(self) -> str:
        return self.AUTHORIZATION_ENDPOINT

    @property
    def token_endpoint(self) -> str:
        return self.TOKEN_ENDPOINT

    @property
    def supports_pkce(self) -> bool:
        return self.SUPPORTS_PKCE

    def build_authorization_url(self, state: str, **extra_params: Any) -> str:
        """Build OAuth authorization URL with state."""
        _RESERVED = {"client_id", "redirect_uri", "response_type", "scope", "state"}
        reserved = _RESERVED | set(self._get_authorization_params())
        conflicts = reserved & set(extra_params.keys())
        if conflicts:
            raise ValueError(f"Cannot override reserved OAuth params: {conflicts}")
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            **self._get_authorization_params(),
            **extra_params,
        }
        return f"{self.authorization_endpoint}?{urlencode(params)}"

    @abstractmethod
    def _get_authorization_params(self) -> dict[str, Any]:
        """Provider-specific auth params."""
        ...

    async def exchange_code_for_tokens(
        self, code: str, **extra_params: Any
    ) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                    **extra_params,
                },
            )
            if response.status_code != 200:
                logger.error(
                    "%s token exchange failed: status=%d",
                    self.provider_name,
                    response.status_code,
                )
                raise ValueError(
                    f"Token exchange failed with status {response.status_code}"
                )
            token_data: dict[str, Any] = response.json()
            return self._normalize_token_response(token_data)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if response.status_code != 200:
                logger.error(
                    "%s token refresh failed: status=%d",
                    self.provider_name,
                    response.status_code,
                )
                raise ValueError(
                    f"Token refresh failed with status {response.status_code}"
                )
            token_data = response.json()
            tokens = self._normalize_token_response(token_data)
            if not tokens.refresh_token:
                tokens = OAuthTokens(
                    access_token=tokens.access_token,
                    refresh_token=refresh_token,
                    token_type=tokens.token_type,
                    expires_in=tokens.expires_in,
                    expires_at=tokens.expires_at,
                    scope=tokens.scope,
                    provider_metadata=tokens.provider_metadata,
                )
            return tokens

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from provider."""
        ...

    def _normalize_token_response(self, token_data: dict[str, Any]) -> OAuthTokens:
        """Normalize provider response to OAuthTokens."""
        expires_in = token_data.get("expires_in", 3600)
        expires_at = utc_now() + timedelta(seconds=expires_in)
        safe_metadata = {
            k: v
            for k, v in token_data.items()
            if k not in self._SENSITIVE_KEYS
        }
        return OAuthTokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=expires_in,
            expires_at=expires_at,
            scope=token_data.get("scope", " ".join(self.scopes)),
            provider_metadata=safe_metadata,
        )


class GmailDriver(OAuthDriver):
    """Gmail/Google OAuth driver."""

    PROVIDER_NAME = "Gmail"
    PROVIDER_TYPE = "gmail"
    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def _get_authorization_params(self) -> dict[str, Any]:
        return {
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                logger.error(
                    "%s get user info failed: status=%d",
                    self.PROVIDER_NAME,
                    response.status_code,
                )
                raise ValueError(
                    f"Failed to get user info with status {response.status_code}"
                )
            data = response.json()
            # Gmail profile API does not return a stable user ID (historyId is a
            # mailbox change marker). Use People API or ID token 'sub' for a stable ID.
            return OAuthUserInfo(
                email=data["emailAddress"],
                name=None,
                picture=None,
                provider_user_id=None,
                provider_metadata=data,
            )


class OutlookDriver(OAuthDriver):
    """Microsoft Outlook/Office 365 OAuth driver."""

    PROVIDER_NAME = "Microsoft 365"
    PROVIDER_TYPE = "outlook"
    AUTHORIZATION_ENDPOINT = (
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    )
    TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    def _get_authorization_params(self) -> dict[str, Any]:
        return {"response_mode": "query"}

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                logger.error(
                    "%s get user info failed: status=%d",
                    self.PROVIDER_NAME,
                    response.status_code,
                )
                raise ValueError(
                    f"Failed to get user info with status {response.status_code}"
                )
            data = response.json()
            email = data.get("mail") or data.get("userPrincipalName")
            if not email:
                raise ValueError("Microsoft account has no email")
            return OAuthUserInfo(
                email=email,
                name=data.get("displayName"),
                picture=None,
                provider_user_id=data.get("id"),
                provider_metadata=data,
            )


class YahooDriver(OAuthDriver):
    """Yahoo Mail OAuth driver."""

    PROVIDER_NAME = "Yahoo Mail"
    PROVIDER_TYPE = "yahoo"
    AUTHORIZATION_ENDPOINT = "https://api.login.yahoo.com/oauth2/request_auth"
    TOKEN_ENDPOINT = "https://api.login.yahoo.com/oauth2/get_token"

    def _get_authorization_params(self) -> dict[str, Any]:
        return {}

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.login.yahoo.com/openid/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                logger.error(
                    "%s get user info failed: status=%d",
                    self.PROVIDER_NAME,
                    response.status_code,
                )
                raise ValueError(
                    f"Failed to get user info with status {response.status_code}"
                )
            data = response.json()
            return OAuthUserInfo(
                email=data["email"],
                name=data.get("name"),
                picture=data.get("picture"),
                provider_user_id=data.get("sub"),
                provider_metadata=data,
            )


class OAuthDriverRegistry:
    """Registry for OAuth drivers by provider type."""

    _drivers: ClassVar[dict[str, type[OAuthDriver]]] = {
        "gmail": GmailDriver,
        "outlook": OutlookDriver,
        "yahoo": YahooDriver,
    }

    @classmethod
    def register(cls, provider_type: str, driver_class: type[OAuthDriver]) -> None:
        cls._drivers[provider_type] = driver_class
        logger.info("Registered OAuth driver: %s", provider_type)

    @classmethod
    def get_driver(
        cls,
        provider_type: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> OAuthDriver:
        if provider_type not in cls._drivers:
            raise ValueError(
                f"Unsupported provider: {provider_type}. "
                f"Supported: {', '.join(cls._drivers)}"
            )
        return cls._drivers[provider_type](
            client_id, client_secret, redirect_uri, scopes
        )

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._drivers.keys())

    @classmethod
    def get_provider_metadata(cls, provider_type: str) -> dict[str, Any]:
        if provider_type not in cls._drivers:
            raise ValueError(f"Unknown provider: {provider_type}")
        d = cls._drivers[provider_type]
        return {
            "provider_type": d.PROVIDER_TYPE,
            "provider_name": d.PROVIDER_NAME,
            "authorization_endpoint": d.AUTHORIZATION_ENDPOINT,
            "token_endpoint": d.TOKEN_ENDPOINT,
            "supports_pkce": d.SUPPORTS_PKCE,
        }
