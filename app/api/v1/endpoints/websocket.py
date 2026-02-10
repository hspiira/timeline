"""WebSocket endpoint: single /ws that uses the connection manager from app.state.

Uses only the injected ConnectionManager (set in lifespan); no manual construction.
Requires a valid JWT via query param ?token=... before registering the connection.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


async def _reject_websocket(websocket: WebSocket, reason: str, code: int = 1008) -> None:
    """Accept then immediately close with code/reason so client gets a proper close frame."""
    await websocket.accept()
    await websocket.close(code=code, reason=reason)


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    """Accept WebSocket only after validating token; register with manager and handle disconnect.

    Token must be provided as query param (e.g. ?token=<jwt>). Connection manager is on
    app.state.ws_manager (set in lifespan).
    """
    manager = websocket.app.state.ws_manager
    token = websocket.query_params.get("token")
    if not token:
        await _reject_websocket(websocket, "Missing token")
        return
    try:
        from app.infrastructure.security.jwt import verify_token

        payload = verify_token(token)
        if not payload.get("sub") or not payload.get("tenant_id"):
            await _reject_websocket(websocket, "Invalid token")
            return
    except ValueError:
        await _reject_websocket(websocket, "Invalid token")
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass
    except Exception:
        raise
    finally:
        await manager.disconnect(websocket)
