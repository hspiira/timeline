"""Request ID middleware.

Generates or forwards X-Request-ID and sets it on the response for tracing.
Client-provided values are sanitized (length + character set) to prevent log injection.
Uses raw ASGI (no BaseHTTPMiddleware) for production-safe streaming and background tasks.
"""

import re
import uuid
from typing import Callable

# Safe for logging: alphanumeric, hyphen, underscore; max length to avoid abuse.
REQUEST_ID_MAX_LENGTH = 64
REQUEST_ID_ALLOWED_PATTERN = re.compile(
    r"^[a-zA-Z0-9_-]{1," + str(REQUEST_ID_MAX_LENGTH) + r"}$"
)


def _get_header(scope: dict, name: str) -> str | None:
    """Return first header value for name (case-insensitive). Headers are (bytes, bytes)."""
    want = name.lower().encode()
    for k, v in scope.get("headers", []):
        if k.lower() == want:
            return v.decode("utf-8", errors="replace")
    return None


def _sanitize_request_id(raw: str | None) -> str:
    """Return raw if valid and safe; otherwise return a new UUID. Prevents log injection."""
    if not raw or not REQUEST_ID_ALLOWED_PATTERN.match(raw.strip()):
        return str(uuid.uuid4())
    return raw.strip()[:REQUEST_ID_MAX_LENGTH]


def RequestIDMiddleware(app: Callable, header_name: str = "X-Request-ID") -> Callable:
    """Add or forward X-Request-ID on each request and response. Raw ASGI."""

    async def asgi_app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        raw = _get_header(scope, header_name)
        request_id = _sanitize_request_id(raw)
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((header_name.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        await app(scope, receive, send_wrapper)

    return asgi_app
