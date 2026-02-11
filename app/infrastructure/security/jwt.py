"""JWT token creation and verification for authentication.

Uses app.core.config for secret and algorithm; app.shared.utils for UTC time.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import PyJWTError

from app.core.config import get_settings


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


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT. Returns the payload.

    Enforces presence of exp and sub. Raises ValueError if the token is
    invalid, expired, or missing required claims.

    Args:
        token: JWT string (e.g. from Authorization header).

    Returns:
        Decoded payload dict.

    Raises:
        ValueError: If token is invalid, expired, or missing required claims.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
    except PyJWTError as e:
        raise ValueError(f"Invalid token: {e!s}") from e
    if "sub" not in payload:
        raise ValueError("Token missing required claim: sub")
    return payload
