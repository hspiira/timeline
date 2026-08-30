"""Health check API schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response for GET /health (liveness)."""

    status: str = Field(default="ok", description="Service status")


class ReadinessResponse(BaseModel):
    """Response for GET /health/ready when ready."""

    status: str = Field(default="ok", description="Readiness status")


class ReadinessErrorResponse(BaseModel):
    """Response for GET /health/ready when RLS check fails (503)."""

    status: str = Field(default="not_ready", description="Readiness status")
    message: str = Field(..., description="Reason (e.g. RLS check failed)")
