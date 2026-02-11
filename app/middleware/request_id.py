"""Request ID middleware.

Generates or forwards X-Request-ID and sets it on the response for tracing.
Client-provided values are sanitized (length + character set) to prevent log injection.
"""

import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Safe for logging: alphanumeric, hyphen, underscore; max length to avoid abuse.
REQUEST_ID_MAX_LENGTH = 64
REQUEST_ID_ALLOWED_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1," + str(REQUEST_ID_MAX_LENGTH) + r"}$")


def _sanitize_request_id(raw: str | None) -> str:
    """Return raw if valid and safe; otherwise return a new UUID. Prevents log injection."""
    if not raw or not REQUEST_ID_ALLOWED_PATTERN.match(raw.strip()):
        return str(uuid.uuid4())
    return raw.strip()[:REQUEST_ID_MAX_LENGTH]


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add or forward X-Request-ID on each request and response."""

    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        """Set request_id from header (sanitized) or generate; add to response."""
        raw = request.headers.get(self.header_name)
        request_id = _sanitize_request_id(raw)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response
