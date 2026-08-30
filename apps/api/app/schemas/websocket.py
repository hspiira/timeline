"""WebSocket API schemas."""

from pydantic import BaseModel, Field


class WebSocketStatusResponse(BaseModel):
    """Response for GET /ws/status (connection count)."""

    total_connections: int = Field(..., description="Number of active WebSocket connections")
