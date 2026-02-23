"""Application lifespan: startup and shutdown.

Single place for all startup/shutdown logic (SRP). Used by main.py;
no business logic here, only wiring of infrastructure (cache,
WebSocket manager, telemetry, DB engine dispose).
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.verification_job_store import VerificationJobStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup then yield; on exit run shutdown.

    Startup order: WebSocket manager, Redis cache (if enabled),
    telemetry (if enabled). Shutdown order: shared HTTP client close,
    cache disconnect, telemetry shutdown, SQL engine dispose.
    """
    settings = get_settings()

    # ---- Startup ----
    # Shared HTTP client for OAuth and other outbound calls (connection reuse).
    app.state.oauth_http_client = httpx.AsyncClient(timeout=30.0)

    from app.api.websocket import ConnectionManager

    app.state.ws_manager = ConnectionManager()
    app.state.verification_job_store = VerificationJobStore()

    if settings.redis_enabled:
        from app.infrastructure.cache.redis_cache import CacheService
        from app.infrastructure.messaging.redis_pubsub import run_sync_progress_broadcast

        cache = CacheService()
        await cache.connect()
        app.state.cache = cache
        sync_broadcast_task = asyncio.create_task(run_sync_progress_broadcast(app))
        app.state.sync_progress_broadcast_task = sync_broadcast_task
    else:
        app.state.cache = None
        app.state.sync_progress_broadcast_task = None

    if settings.telemetry_enabled:
        from app.shared.telemetry.telemetry import TelemetryConfig, set_telemetry

        telemetry = TelemetryConfig(
            service_name=settings.app_name,
            service_version=settings.app_version,
            enabled=True,
            environment=settings.telemetry_environment,
        )
        telemetry.setup_telemetry(
            exporter_type=settings.telemetry_exporter,
            otlp_endpoint=settings.telemetry_otlp_endpoint,
            jaeger_endpoint=settings.telemetry_jaeger_endpoint,
            sample_rate=settings.telemetry_sample_rate,
        )
        set_telemetry(telemetry)
        telemetry.instrument_fastapi(app)
        logger.info("Telemetry initialized")

    yield

    # ---- Shutdown ----
    if getattr(app.state, "oauth_http_client", None) is not None:
        await app.state.oauth_http_client.aclose()
        app.state.oauth_http_client = None
        logger.info("OAuth HTTP client closed")

    sync_task = getattr(app.state, "sync_progress_broadcast_task", None)
    if sync_task is not None:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
        logger.info("Sync progress broadcast task stopped")

    if getattr(app.state, "cache", None) is not None:
        await app.state.cache.disconnect()
        logger.info("Cache disconnected")

    from app.shared.telemetry.telemetry import get_telemetry

    telemetry_instance = get_telemetry()
    if telemetry_instance is not None:
        telemetry_instance.shutdown()
        logger.info("Telemetry shutdown complete")

    from app.infrastructure.persistence import database

    if getattr(database, "engine", None) is not None:
        database.engine.dispose()
        logger.info("Database engine disposed")
