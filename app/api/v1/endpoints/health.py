"""Health check endpoint. No dependencies; used for liveness and readiness probes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
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
async def readiness_check() -> ReadinessResponse | JSONResponse:
    """Return 200 if ready; 503 if RLS readiness check is enabled and fails.

    When RLS_READINESS_CHECK is True, runs RLS checks (app role must not have
    BYPASSRLS; optionally policies exist). Use for Kubernetes/orchestrator
    readiness probes in production.
    """
    settings = get_settings()
    if not settings.rls_readiness_check:
        return ReadinessResponse()

    from urllib.parse import urlparse

    from app.infrastructure.persistence.rls_check import run_rls_check

    app_role = settings.rls_check_app_role
    if not app_role and settings.database_url:
        parsed = urlparse(settings.database_url)
        app_role = parsed.username

    result = await run_rls_check(
        database_url=settings.database_url,
        app_role=app_role,
        migrator_role=None,
        check_policies=settings.rls_check_policies,
    )

    if result.ok:
        return ReadinessResponse()
    return JSONResponse(
        status_code=503,
        content=ReadinessErrorResponse(
            status="not_ready",
            message=result.message,
        ).model_dump(),
    )
