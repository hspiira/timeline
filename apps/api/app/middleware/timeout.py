"""Request timeout middleware.

Cancels the request if it runs longer than the configured timeout (asyncio.wait_for).
Uses raw ASGI (no BaseHTTPMiddleware) for production-safe streaming and background tasks.
"""

import asyncio
import json
import logging
from typing import Callable

logger = logging.getLogger(__name__)


def TimeoutMiddleware(app: Callable, timeout_seconds: int) -> Callable:
    """Cancel request after timeout_seconds (sends 504 on timeout). Raw ASGI."""

    async def asgi_app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        try:
            await asyncio.wait_for(
                app(scope, receive, send),
                timeout=float(timeout_seconds),
            )
        except asyncio.TimeoutError:
            method = scope.get("method", "")
            path = scope.get("path", "")
            logger.warning(
                "Request timed out after %s seconds: %s %s",
                timeout_seconds,
                method,
                path,
            )
            body = json.dumps(
                {
                    "error": "GATEWAY_TIMEOUT",
                    "message": f"Request timed out after {timeout_seconds} seconds",
                    "details": {"timeout_seconds": timeout_seconds},
                }
            ).encode()
            await send({
                "type": "http.response.start",
                "status": 504,
                "headers": [
                    (b"content-type", b"application/json"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })

    return asgi_app
