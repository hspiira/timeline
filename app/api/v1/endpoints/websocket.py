"""WebSocket endpoint: single /ws that uses the connection manager from app.state.

Uses only the injected ConnectionManager (set in lifespan); no manual construction.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Accept WebSocket connection and register with manager; handle disconnect.

    Connection manager is on app.state.ws_manager (set in lifespan).
    """
    manager = websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or broadcast; minimal implementation echoes to sender only.
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
        raise
