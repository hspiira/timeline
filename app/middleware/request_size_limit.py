"""Request body size limit middleware.

Rejects requests with Content-Length exceeding the configured maximum (e.g. max_upload_size).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds max_bytes."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        """Return 413 if Content-Length > max_bytes."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body must be at most {self.max_bytes} bytes",
                            "details": {"max_bytes": self.max_bytes, "content_length": length},
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)
