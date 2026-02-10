"""Request timeout middleware.

Cancels the request if it runs longer than the configured timeout (asyncio.wait_for).
"""

import asyncio
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Cancel request after timeout_seconds (raises asyncio.TimeoutError → 504)."""

    def __init__(self, app, timeout_seconds: int):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        """Run the request with a timeout; return 504 on timeout."""
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=float(self.timeout_seconds),
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Request timed out after %s seconds: %s %s",
                self.timeout_seconds,
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "error": "GATEWAY_TIMEOUT",
                    "message": f"Request timed out after {self.timeout_seconds} seconds",
                    "details": {"timeout_seconds": self.timeout_seconds},
                },
            )
