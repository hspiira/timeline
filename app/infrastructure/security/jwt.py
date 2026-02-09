"""JWT token creation and verification for authentication.

Uses app.core.config for secret and algorithm; app.shared.utils for UTC time.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

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
    encoded = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    assert isinstance(encoded, str)
    return encoded


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT. Returns the payload.

    Args:
        token: JWT string (e.g. from Authorization header).

    Returns:
        Decoded payload dict.

    Raises:
        ValueError: If token is invalid or expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e!s}") from e
