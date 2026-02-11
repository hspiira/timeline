"""Correlation ID middleware.

Propagates X-Correlation-ID for distributed tracing (forward from client or use request ID).
Uses raw ASGI (no BaseHTTPMiddleware) for production-safe streaming and background tasks.
"""

import uuid
from typing import Callable


def _get_header(scope: dict, name: str) -> str | None:
    """Return first header value for name (case-insensitive)."""
    want = name.lower().encode()
    for k, v in scope.get("headers", []):
        if k.lower() == want:
            return v.decode("utf-8", errors="replace")
    return None


def CorrelationIDMiddleware(
    app: Callable, header_name: str = "X-Correlation-ID"
) -> Callable:
    """Add or forward X-Correlation-ID; fall back to request_id if set on scope state. Raw ASGI."""

    async def asgi_app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        correlation_id = _get_header(scope, header_name)
        if not correlation_id:
            correlation_id = scope.get("state", {}).get("request_id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((header_name.encode(), correlation_id.encode()))
                message["headers"] = headers
            await send(message)

        await app(scope, receive, send_wrapper)

    return asgi_app
