"""Shared helpers for audit logging: derive request metadata from Starlette Request."""

from __future__ import annotations

from starlette.requests import Request

# Path prefix to strip (e.g. /api/v1) then first segment = resource_type, second = resource_id
_API_PREFIX = "/api/v1"


def get_audit_request_context(request: Request) -> tuple[str | None, str | None, str | None]:
    """Return (request_id, ip_address, user_agent) for audit log entries.

    Single source of truth for deriving client identity from the request:
    request_id from request state, IP from X-Forwarded-For (first hop) or
    request.client.host, user_agent from header.
    """
    request_id = getattr(request.state, "request_id", None)
    client_host = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    ip_address = (
        (forwarded.split(",")[0].strip() if forwarded else None) or client_host
    )
    user_agent = request.headers.get("User-Agent")
    return (request_id, ip_address, user_agent)


def get_tenant_and_user_for_audit(request: Request) -> tuple[str | None, str | None]:
    """Return (tenant_id, user_id) from header and JWT for audit. None if missing."""
    from app.core.config import get_settings
    from app.infrastructure.security.jwt import verify_token

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


def get_audit_resource_from_path(path: str) -> tuple[str, str | None]:
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


def get_audit_action_from_method(method: str) -> str:
    """Map HTTP method to audit action."""
    return {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method, method.lower())
