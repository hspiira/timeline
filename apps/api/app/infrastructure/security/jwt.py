"""JWT token creation and verification for authentication.

Uses app.core.config for secret and algorithm; app.shared.utils for UTC time.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import PyJWTError

from app.core.config import get_settings


ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with the given claims.

    Args:
        data: Claims to encode (e.g. tenant_id, user_id, sub).
        expires_delta: Optional TTL; else uses settings.access_token_expire_minutes.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()
    to_encode["typ"] = ACCESS_TOKEN_TYPE
    if expires_delta is not None:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token, used only to mint new access tokens.

    Marked with ``typ=refresh`` so :func:`verify_token` will refuse it wherever an
    access token is expected. Keep the claims minimal — it is not an access grant.

    Args:
        data: Claims to encode (sub, and tenant_id so the renewed access token
            stays scoped to the organisation the person signed in to).
        expires_delta: Optional TTL; else uses settings.refresh_token_expire_days.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()
    to_encode["typ"] = REFRESH_TOKEN_TYPE
    if expires_delta is not None:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def verify_token(
    token: str, expected_type: str = ACCESS_TOKEN_TYPE
) -> dict[str, Any]:
    """Verify and decode a JWT. Returns the payload.

    Enforces presence of exp and sub, and that the token is of the expected kind, so
    a refresh token cannot be presented as an access token to reach the API.

    Args:
        token: JWT string (e.g. from Authorization header).
        expected_type: ``access`` or ``refresh``.

    Returns:
        Decoded payload dict.

    Raises:
        ValueError: If the token is invalid, expired, missing required claims, or of
            the wrong kind.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except PyJWTError as e:
        raise ValueError("Invalid token") from e
    if payload.get("typ", ACCESS_TOKEN_TYPE) != expected_type:
        raise ValueError("Invalid token")
    return payload
