"""Health check endpoint. Liveness has no deps; readiness uses Depends(get_rls_readiness_result)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_rls_readiness_result
from app.infrastructure.persistence.rls_check import RLSCheckResult
from app.schemas.health import (
    HealthResponse,
    ReadinessErrorResponse,
    ReadinessResponse,
)

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return simple ok status for liveness."""
    return HealthResponse()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"description": "Not ready (e.g. RLS check failed)", "model": ReadinessErrorResponse}},
)
async def readiness_check(
    result: Annotated[RLSCheckResult, Depends(get_rls_readiness_result)],
) -> ReadinessResponse | JSONResponse:
    """Return 200 if ready; 503 if RLS readiness check is enabled and fails.

    When RLS_READINESS_CHECK is True, RLS checks run via get_rls_readiness_result
    (app role must not have BYPASSRLS; optionally policies exist). Use for
    Kubernetes/orchestrator readiness probes in production.
    """
    if result.ok:
        return ReadinessResponse()
    return JSONResponse(
        status_code=503,
        content=ReadinessErrorResponse(
            status="not_ready",
            message=result.message,
        ).model_dump(),
    )
