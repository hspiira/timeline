"""WebSocket connection manager and dependencies.

Used by the WebSocket endpoint to broadcast and manage connections.
"""

from app.api.websocket.manager import ConnectionManager

__all__ = ["ConnectionManager"]
