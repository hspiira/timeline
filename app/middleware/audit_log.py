"""API audit log middleware.

Logs successful mutations (POST/PUT/PATCH/DELETE 2xx) to audit_log table.
Runs only when database_backend is postgres. Infers resource_type and resource_id from path.
"""

from __future__ import annotations

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
import app.infrastructure.persistence.database as database
from app.infrastructure.security.jwt import verify_token
from app.infrastructure.services.api_audit_log_service import ApiAuditLogService

logger = logging.getLogger(__name__)

# Path prefix to strip (e.g. /api/v1) then first segment = resource_type, second = resource_id
_API_PREFIX = "/api/v1"


def _get_tenant_and_user(request: Request) -> tuple[str | None, str | None]:
    """Return (tenant_id, user_id) from header and JWT. None if missing."""
    settings = get_settings()
    tenant_id = request.headers.get(settings.tenant_header_name)
    user_id = None
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        try:
            payload = verify_token(auth[7:].strip())
            user_id = payload.get("sub")
            if not tenant_id and payload.get("tenant_id"):
                tenant_id = payload.get("tenant_id")
        except Exception:
            pass
    return (tenant_id, user_id)


def _resource_from_path(path: str) -> tuple[str, str | None]:
    """Infer (resource_type, resource_id) from path. E.g. /api/v1/subjects/abc -> (subjects, abc)."""
    if not path.startswith(_API_PREFIX + "/"):
        return ("", None)
    rest = path[len(_API_PREFIX) :].strip("/")
    if not rest:
        return ("", None)
    parts = rest.split("/")
    resource_type = parts[0] if parts else ""
    resource_id = parts[1] if len(parts) > 1 else None
    return (resource_type, resource_id)


def _action_from_method(method: str) -> str:
    """Map HTTP method to audit action."""
    return {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method, method.lower())


def AuditLogMiddleware(app: Callable) -> Callable:
    """Log successful mutations to audit_log. No-op when not postgres."""

    class _Middleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            response = await call_next(request)
            database._ensure_engine()
            if database.AsyncSessionLocal is None:
                return response
            if get_settings().database_backend != "postgres":
                return response
            method = request.method
            if method not in ("POST", "PUT", "PATCH", "DELETE"):
                return response
            if not (200 <= response.status_code < 300):
                return response
            tenant_id, user_id = _get_tenant_and_user(request)
            if not tenant_id:
                return response
            resource_type, resource_id = _resource_from_path(request.url.path)
            if not resource_type:
                return response
            request_id = getattr(request.state, "request_id", None)
            client_host = request.client.host if request.client else None
            forwarded = request.headers.get("X-Forwarded-For")
            ip_address = (forwarded.split(",")[0].strip() if forwarded else None) or client_host
            user_agent = request.headers.get("User-Agent")
            action = _action_from_method(method)
            try:
                async with database.AsyncSessionLocal() as session:
                    async with session.begin():
                        svc = ApiAuditLogService(session)
                        await svc.log_action(
                            tenant_id=tenant_id,
                            user_id=user_id,
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            old_values=None,
                            new_values=None,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            request_id=request_id,
                            success=True,
                            error_message=None,
                        )
            except Exception as e:
                logger.warning("Failed to write audit log: %s", e, exc_info=True)
            return response

    return _Middleware(app)
