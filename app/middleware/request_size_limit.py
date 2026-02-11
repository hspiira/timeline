"""Request body size limit middleware.

Rejects requests whose body exceeds the configured maximum (e.g. max_upload_size).
Enforces the limit for both Content-Length and Transfer-Encoding: chunked.
Uses raw ASGI (no BaseHTTPMiddleware) for production-safe streaming and background tasks.
"""

import json
from typing import Any, Callable


def _get_header(scope: dict, name: str) -> str | None:
    """Return first header value for name (case-insensitive)."""
    want = name.lower().encode()
    for k, v in scope.get("headers", []):
        if k.lower() == want:
            return v.decode("utf-8", errors="replace")
    return None


async def _send_413(send: Callable, max_bytes: int, actual: int | None = None) -> None:
    """Send 413 Payload Too Large response."""
    details: dict[str, Any] = {"max_bytes": max_bytes}
    if actual is not None:
        details["content_length"] = actual
    body = json.dumps(
        {
            "error": "PAYLOAD_TOO_LARGE",
            "message": f"Request body must be at most {max_bytes} bytes",
            "details": details,
        }
    ).encode()
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({
        "type": "http.response.body",
        "body": body,
        "more_body": False,
    })


def RequestSizeLimitMiddleware(app: Callable, max_bytes: int) -> Callable:
    """Reject requests whose body exceeds max_bytes (Content-Length or chunked). Raw ASGI."""

    async def asgi_app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        content_length_str = _get_header(scope, "content-length")
        if content_length_str:
            try:
                length = int(content_length_str)
                if length > max_bytes:
                    await _send_413(send, max_bytes, length)
                    return
            except ValueError:
                pass
            await app(scope, receive, send)
            return

        transfer_encoding = (
            (_get_header(scope, "transfer-encoding") or "").lower()
        )
        if transfer_encoding == "chunked" or not content_length_str:
            chunks: list[bytes] = []
            total = 0
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    continue
                body = message.get("body", b"")
                total += len(body)
                if total > max_bytes:
                    await _send_413(send, max_bytes, total)
                    return
                chunks.append(body)
                if not message.get("more_body", False):
                    break

            class ReplayReceive:
                """Replay collected body chunks to the app one message at a time."""

                def __init__(self) -> None:
                    self._index = 0

                async def __call__(self) -> dict:
                    if self._index < len(chunks):
                        i = self._index
                        self._index += 1
                        return {
                            "type": "http.request",
                            "body": chunks[i],
                            "more_body": self._index < len(chunks),
                        }
                    return {"type": "http.request", "body": b"", "more_body": False}

            await app(scope, ReplayReceive(), send)
            return

        await app(scope, receive, send)
    return asgi_app
