"""Application lifespan: startup and shutdown.

Single place for all startup/shutdown logic (SRP). Used by main.py;
no business logic here, only wiring of infrastructure (Firebase, cache,
WebSocket manager, telemetry, DB engine dispose).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup then yield; on exit run shutdown.

    Startup order: Firebase, WebSocket manager, Redis cache (if enabled),
    telemetry (if enabled). Shutdown order: cache disconnect, telemetry
    shutdown, SQL engine dispose (if postgres).
    """
    settings = get_settings()

    # ---- Startup ----
    from app.infrastructure.firebase import init_firebase

    fb_initialized = init_firebase()
    logger.info("Firebase initialized: %s", fb_initialized)

    from app.api.websocket import ConnectionManager

    app.state.ws_manager = ConnectionManager()

    if settings.redis_enabled:
        from app.infrastructure.cache.redis_cache import CacheService

        cache = CacheService()
        await cache.connect()
        app.state.cache = cache
    else:
        app.state.cache = None

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
