"""Security headers middleware.

Adds common security-related response headers (X-Content-Type-Options, etc.).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set security headers on all responses."""

    # Default headers; override via constructor if needed.
    DEFAULT_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    def __init__(self, app, headers: dict[str, str] | None = None):
        super().__init__(app)
        self.headers = headers if headers is not None else self.DEFAULT_HEADERS.copy()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)
        for name, value in self.headers.items():
            response.headers.setdefault(name, value)
        return response
