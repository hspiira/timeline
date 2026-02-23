"""API audit log middleware.

Audit logging is done in the same transaction as the request via the
ensure_audit_logged dependency on write endpoints. This middleware is
kept as a no-op for backwards compatibility (can be removed from the
stack if desired).
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def AuditLogMiddleware(app: Callable) -> Callable:
    """No-op. Audit is written by ensure_audit_logged dependency (same transaction)."""

    class _Middleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            return await call_next(request)

    return _Middleware(app)
