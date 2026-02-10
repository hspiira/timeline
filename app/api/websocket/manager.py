"""WebSocket connection manager.

Holds active connections and provides broadcast. Use via Depends(get_connection_manager)
or app.state so the WebSocket endpoint does not construct it manually (DIP).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcast.

    Responsibilities:
    - Track active connections (e.g. per tenant or global).
    - Accept new connections and remove on disconnect.
    - Broadcast messages to all or a subset of connections.
    """

    def __init__(self) -> None:
        """Initialize with empty connection set."""
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection.

        Args:
            websocket: The WebSocket instance to accept and track.
        """
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection from the set (call on disconnect).

        Args:
            websocket: The WebSocket instance to remove.
        """
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast(self, message: str | dict[str, Any]) -> None:
        """Send a message to all connected clients.

        Args:
            message: String or JSON-serializable dict to send.
        """
        async with self._lock:
            snapshot = list(self._connections)
        dead: list[WebSocket] = []
        for ws in snapshot:
            try:
                if isinstance(message, dict):
                    await ws.send_json(message)
                else:
                    await ws.send_text(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self._connections)
