"""WebSocket endpoint: single /ws and GET /status.

Uses only the ConnectionManager on app.state (set in lifespan); no manual construction.
Requires a valid JWT before registering the connection. The token travels in the
Sec-WebSocket-Protocol header rather than the query string, because query strings are
routinely recorded in proxy and server access logs and a bearer token in a log file
outlives the request that carried it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from app.api.v1.dependencies import get_tenant_id, require_permission
from app.schemas.websocket import WebSocketStatusResponse

router = APIRouter()


@router.get("/status", response_model=WebSocketStatusResponse)
async def websocket_status(
    request: Request,
    _: Annotated[object, Depends(require_permission("tenant", "read"))] = None,
) -> WebSocketStatusResponse:
    """Return WebSocket connection count for monitoring. Requires tenant read permission (e.g. admin)."""
    manager = getattr(request.app.state, "ws_manager", None)
    total_connections = (
        await manager.get_connection_count() if manager else 0
    )
    return WebSocketStatusResponse(total_connections=total_connections)


BEARER_SUBPROTOCOL = "bearer"


def _token_from_subprotocol(websocket: WebSocket) -> str | None:
    """Extract the bearer token a client offered in Sec-WebSocket-Protocol.

    Clients offer two values, the marker "bearer" followed by the JWT. Anything else
    is treated as no token at all.
    """
    header = websocket.headers.get("sec-websocket-protocol")
    if not header:
        return None
    offered = [part.strip() for part in header.split(",") if part.strip()]
    if len(offered) != 2 or offered[0] != BEARER_SUBPROTOCOL:
        return None
    return offered[1]


async def _reject_websocket(
    websocket: WebSocket,
    reason: str,
    code: int = 1008,
    *,
    subprotocol: str | None = None,
) -> None:
    """Accept then immediately close with code/reason so client gets a proper close frame.

    The offered subprotocol is echoed back even when rejecting, because a browser fails
    the handshake outright if the server selects none, and the client would then see a
    generic error instead of the reason.
    """
    await websocket.accept(subprotocol=subprotocol)
    await websocket.close(code=code, reason=reason)


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    """Accept WebSocket only after validating token; register with manager and handle disconnect.

    The client offers Sec-WebSocket-Protocol: bearer, <jwt>. Connection manager is on
    app.state.ws_manager (set in lifespan).
    """
    manager = websocket.app.state.ws_manager
    token = _token_from_subprotocol(websocket)
    if not token:
        await _reject_websocket(websocket, "Missing token")
        return
    try:
        from app.infrastructure.security.jwt import verify_token

        payload = verify_token(token)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            await _reject_websocket(
                websocket, "Invalid token", subprotocol=BEARER_SUBPROTOCOL
            )
            return
    except ValueError:
        await _reject_websocket(
            websocket, "Invalid token", subprotocol=BEARER_SUBPROTOCOL
        )
        return

    await manager.connect(
        websocket, tenant_id=tenant_id, subprotocol=BEARER_SUBPROTOCOL
    )
    try:
        while True:
            await websocket.receive_text()
            # Placeholder: drain messages until disconnect. Real push/notify
            # can use manager.broadcast_to_tenant(tenant_id, message).
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
