"""Health/readiness dependencies (composition root)."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import get_settings
from app.infrastructure.persistence.rls_check import RLSCheckResult, run_rls_check


async def get_rls_readiness_result() -> RLSCheckResult:
    """Compute RLS readiness result from settings for the readiness probe.

    When RLS_READINESS_CHECK is False, returns ok=True without running checks.
    Otherwise runs run_rls_check with database_url, app_role (from settings or
    derived from database_url username), and check_policies flag.

    Returns:
        RLSCheckResult with ok=True if ready, ok=False and message otherwise.
    """
    settings = get_settings()
    if not settings.rls_readiness_check:
        return RLSCheckResult(ok=True, message="RLS check disabled")

    app_role = settings.rls_check_app_role
    if not app_role and settings.database_url:
        parsed = urlparse(settings.database_url)
        app_role = parsed.username

    return await run_rls_check(
        database_url=settings.database_url,
        app_role=app_role,
        migrator_role=None,
        check_policies=settings.rls_check_policies,
    )
