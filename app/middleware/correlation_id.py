"""Correlation ID middleware.

Propagates X-Correlation-ID for distributed tracing (forward from client or use request ID).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add or forward X-Correlation-ID; fall back to request_id if set on request.state."""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        """Set correlation_id from header or from request_id; add to response."""
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id and hasattr(request.state, "request_id"):
            correlation_id = request.state.request_id
        if not correlation_id:
            import uuid
            correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response
