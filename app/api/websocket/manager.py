"""WebSocket connection manager.

Holds active connections per tenant and provides tenant-scoped broadcast.
Use via app.state.ws_manager (set in lifespan). Connections are isolated by tenant_id.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections with tenant isolation.

    - Tracks connections per tenant (connect requires tenant_id).
    - Broadcast can be limited to a tenant or sent to all (e.g. for admin).
    - connection_count is lock-protected for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize with empty per-tenant connection sets."""
        self._connections_by_tenant: dict[str, set[WebSocket]] = {}
        self._websocket_to_tenant: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, tenant_id: str) -> None:
        """Accept and register a new connection for the given tenant.

        Args:
            websocket: The WebSocket instance to accept and track.
            tenant_id: Tenant ID from JWT; used to isolate broadcasts.
        """
        await websocket.accept()
        async with self._lock:
            if tenant_id not in self._connections_by_tenant:
                self._connections_by_tenant[tenant_id] = set()
            self._connections_by_tenant[tenant_id].add(websocket)
            self._websocket_to_tenant[websocket] = tenant_id

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection (call on disconnect).

        Args:
            websocket: The WebSocket instance to remove.
        """
        async with self._lock:
            tenant_id = self._websocket_to_tenant.pop(websocket, None)
            if tenant_id and tenant_id in self._connections_by_tenant:
                conns = self._connections_by_tenant[tenant_id]
                if websocket in conns:
                    conns.remove(websocket)
                if not conns:
                    del self._connections_by_tenant[tenant_id]

    async def broadcast_to_tenant(
        self, tenant_id: str, message: str | dict[str, Any]
    ) -> None:
        """Send a message to all connections in the given tenant.

        Args:
            tenant_id: Target tenant (only their connections receive the message).
            message: String or JSON-serializable dict to send.
        """
        async with self._lock:
            snapshot = list(self._connections_by_tenant.get(tenant_id, set()))
        await self._send_to_list(snapshot, message)

    async def broadcast(self, message: str | dict[str, Any]) -> None:
        """Send a message to all connected clients (all tenants). Use with care.

        Prefer broadcast_to_tenant for tenant-isolated messaging.

        Args:
            message: String or JSON-serializable dict to send.
        """
        async with self._lock:
            snapshot = list(
                ws
                for conns in self._connections_by_tenant.values()
                for ws in conns
            )
        await self._send_to_list(snapshot, message)

    async def _send_to_list(
        self,
        connections: list[WebSocket],
        message: str | dict[str, Any],
    ) -> None:
        """Send message to a list of connections; remove dead ones under lock."""
        dead: list[WebSocket] = []
        for ws in connections:
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
                    tid = self._websocket_to_tenant.pop(ws, None)
                    if tid and tid in self._connections_by_tenant:
                        conns = self._connections_by_tenant[tid]
                        if ws in conns:
                            conns.remove(ws)
                        if not conns:
                            del self._connections_by_tenant[tid]

    async def get_connection_count(self) -> int:
        """Return the total number of active connections (lock-safe)."""
        async with self._lock:
            return sum(len(c) for c in self._connections_by_tenant.values())
