"""Connector health API: admin-only status of platform connectors."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_system_read_permission

router = APIRouter()


def _health_payload(connectors: list, status: str) -> dict:
    """Build response body; serialize ConnectorHealth for JSON (datetime → iso)."""
    out = []
    for h in connectors:
        out.append({
            "connector_id": h.connector_id,
            "status": h.status,
            "last_event_at": h.last_event_at.isoformat() if h.last_event_at else None,
            "error": h.error,
            "lag": h.lag,
        })
    return {"connectors": out, "status": status}


@router.get("/health")
async def connectors_health(
    request: Request,
    _: Annotated[object, Depends(get_system_read_permission)] = None,
):
    """Return health for all registered connectors. 200 if all running, 207 if any degraded, 503 if all stopped."""
    runner = getattr(request.app.state, "connector_runner", None)
    if runner is None:
        return JSONResponse(
            content=_health_payload([], "disabled"),
            status_code=200,
        )

    health_list = await runner.all_health()
    statuses = [h.status for h in health_list]
    if not statuses:
        return _health_payload(health_list, "ok")
    if all(s == "running" for s in statuses):
        return _health_payload(health_list, "ok")
    if all(s == "stopped" for s in statuses):
        return JSONResponse(
            content=_health_payload(health_list, "unavailable"),
            status_code=503,
        )
    return JSONResponse(
        content=_health_payload(health_list, "degraded"),
        status_code=207,
    )
