"""Health check API schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response for GET /health (liveness)."""

    status: str = Field(default="ok", description="Service status")
