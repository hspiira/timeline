"""Request tracking middleware: X-Request-ID and X-Correlation-ID.

Generates or forwards both headers; correlation ID falls back to request ID.
Uses raw ASGI for production-safe streaming and background tasks.
"""

import re
import uuid
from typing import Callable

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


def RequestTrackingMiddleware(
    app: Callable,
    request_id_header: str = "X-Request-ID",
    correlation_id_header: str = "X-Correlation-ID",
) -> Callable:
    """Add or forward X-Request-ID and X-Correlation-ID on each request and response.

    Request ID is sanitized (length + character set) to prevent log injection.
    Correlation ID is taken from header, or falls back to request ID, or generated.
    """

    async def asgi_app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        raw_request_id = _get_header(scope, request_id_header)
        request_id = _sanitize_request_id(raw_request_id)
        scope.setdefault("state", {})["request_id"] = request_id

        correlation_id = _get_header(scope, correlation_id_header)
        if not correlation_id:
            correlation_id = scope.get("state", {}).get("request_id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        scope["state"]["correlation_id"] = correlation_id

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                seen = {h[0].lower() for h in headers}
                for name, value in (
                    (request_id_header, request_id),
                    (correlation_id_header, correlation_id),
                ):
                    name_b = name.encode()
                    if name_b.lower() not in seen:
                        headers.append((name_b, value.encode()))
                        seen.add(name_b.lower())
                message["headers"] = headers
            await send(message)

        await app(scope, receive, send_wrapper)

    return asgi_app
