"""Request body size limit middleware.

Rejects requests whose body exceeds the configured maximum (e.g. max_upload_size).
Enforces the limit for both Content-Length and Transfer-Encoding: chunked.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def _payload_too_large_response(max_bytes: int, actual: int | None = None) -> Response:
    details: dict = {"max_bytes": max_bytes}
    if actual is not None:
        details["content_length"] = actual
    return JSONResponse(
        status_code=413,
        content={
            "error": "PAYLOAD_TOO_LARGE",
            "message": f"Request body must be at most {max_bytes} bytes",
            "details": details,
        },
    )


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds max_bytes (Content-Length or chunked)."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    return _payload_too_large_response(self.max_bytes, length)
            except ValueError:
                pass
            return await call_next(request)

        if request.headers.get("transfer-encoding", "").lower() == "chunked" or not content_length:
            chunks: list[bytes] = []
            total = 0
            receive = request.receive
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    continue
                body = message.get("body", b"")
                total += len(body)
                if total > self.max_bytes:
                    return _payload_too_large_response(self.max_bytes, total)
                chunks.append(body)
                if not message.get("more_body", False):
                    break

            async def replay_receive_gen():
                for i, body in enumerate(chunks):
                    yield {"type": "http.request", "body": body, "more_body": i < len(chunks) - 1}

            replay_iter = replay_receive_gen()

            async def replayed_receive():
                try:
                    return await replay_iter.__anext__()
                except StopAsyncIteration:
                    return {"type": "http.request", "body": b"", "more_body": False}

            request = Request(request.scope, replayed_receive, request._send)

        return await call_next(request)
