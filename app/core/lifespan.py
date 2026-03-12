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

    Startup order: shared HTTP client, WebSocket manager, Redis cache
    (if enabled), telemetry (if enabled). Shutdown order: shared HTTP
    client close, sync broadcast task cancel, cache disconnect,
    telemetry shutdown, SQL engine dispose.
    """
    settings = get_settings()

    # ---- Startup ----
    # Shared HTTP client for OAuth and other outbound calls (connection reuse).
    app.state.oauth_http_client = httpx.AsyncClient(timeout=30.0)

    from app.api.websocket import ConnectionManager

    app.state.ws_manager = ConnectionManager()
    app.state.pending_webhook_tasks = set()

    from app.infrastructure.external.storage.factory import StorageFactory

    app.state.storage = StorageFactory.create_storage_service()

    app.state.verification_job_store = VerificationJobStore(
        max_age_seconds=settings.verification_job_max_age_seconds,
        grace_period_seconds=settings.verification_job_grace_period_seconds,
    )

    from app.infrastructure.services.event_stream_broadcaster import (
        InMemoryEventStreamBroadcaster,
    )

    if settings.redis_enabled:
        from app.infrastructure.cache.redis_cache import CacheService
        from app.infrastructure.messaging.redis_pubsub import run_sync_progress_broadcast
        from app.infrastructure.services.redis_rate_limiter import RedisRateLimiter

        cache = CacheService()
        await cache.connect()
        app.state.cache = cache
        app.state.event_rate_limiter = (
            RedisRateLimiter(cache.redis) if cache.redis else None
        )
        if cache.redis is not None:
            from app.infrastructure.messaging.event_publisher import (
                RedisEventPublisher,
            )

            app.state.event_stream_broadcaster = RedisEventPublisher(cache.redis)
        else:
            app.state.event_stream_broadcaster = InMemoryEventStreamBroadcaster()
        sync_broadcast_task = asyncio.create_task(run_sync_progress_broadcast(app))
        app.state.sync_progress_broadcast_task = sync_broadcast_task
    else:
        app.state.cache = None
        app.state.event_rate_limiter = None
        app.state.sync_progress_broadcast_task = None
        app.state.event_stream_broadcaster = InMemoryEventStreamBroadcaster()

    from app.projections import register_all_handlers

    register_all_handlers()

    if settings.projection_engine_enabled:
        from app.core.projection_engine_job import run_projection_engine_job

        app.state.projection_engine_task = asyncio.create_task(
            run_projection_engine_job(app), name="projection_engine"
        )
        logger.info("Projection engine started")
    else:
        app.state.projection_engine_task = None

    if settings.chain_anchor_enabled:
        from app.core.anchor_job import run_chain_anchor_job

        app.state.chain_anchor_task = asyncio.create_task(run_chain_anchor_job(app))
        logger.info("Chain anchor job started")
    else:
        app.state.chain_anchor_task = None

    if settings.epoch_sealing_enabled:
        from app.infrastructure.persistence.database import AsyncSessionLocal

        from app.core.epoch_sealing_job import run_epoch_sealing_job

        app.state.epoch_sealing_task = asyncio.create_task(
            run_epoch_sealing_job(
                app.state.oauth_http_client,
                AsyncSessionLocal,
                settings,
            ),
            name="epoch_sealing",
        )
        logger.info("Epoch sealing job started")
    else:
        app.state.epoch_sealing_task = None

    if settings.tsa_batch_enabled:
        from app.core.tsa_batch_job import run_tsa_batch_job

        app.state.tsa_batch_task = asyncio.create_task(
            run_tsa_batch_job(app), name="tsa_batch"
        )
        logger.info("TSA batch job started")
    else:
        app.state.tsa_batch_task = None

    connectors_enabled = (
        settings.connector_cdc_postgres_enabled
        or settings.connector_kafka_enabled
        or settings.connector_email_enabled
        or settings.connector_file_watch_enabled
    )
    if connectors_enabled:
        from app.infrastructure.persistence.database import AsyncSessionLocal

        if AsyncSessionLocal is not None:
            from app.connectors.email.connector import EmailConnector
            from app.connectors.runner import ConnectorRunner, make_event_service_factory

            factory = make_event_service_factory(AsyncSessionLocal, app)
            runner = ConnectorRunner(event_service_factory=factory)
            if settings.connector_email_enabled and settings.connector_email_tenant_id:
                runner.register(
                    EmailConnector(
                        connector_id="email",
                        tenant_id=settings.connector_email_tenant_id,
                        poll_interval_seconds=settings.connector_email_poll_interval_seconds,
                    )
                )
            # CDC, Kafka, file_watch: register when implemented
            app.state.connector_runner = runner
            await runner.start_all()
            app.state.connector_runner_task = None
            logger.info("Connector runner started")
        else:
            app.state.connector_runner = None
            app.state.connector_runner_task = None
            logger.warning("Connectors enabled but database not configured; connector runner disabled")
    else:
        app.state.connector_runner = None
        app.state.connector_runner_task = None

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

    chain_anchor_task = getattr(app.state, "chain_anchor_task", None)
    if chain_anchor_task is not None:
        chain_anchor_task.cancel()
        try:
            await chain_anchor_task
        except asyncio.CancelledError:
            pass
        logger.info("Chain anchor task stopped")

    tsa_batch_task = getattr(app.state, "tsa_batch_task", None)
    if tsa_batch_task is not None:
        tsa_batch_task.cancel()
        try:
            await tsa_batch_task
        except asyncio.CancelledError:
            pass
        logger.info("TSA batch task stopped")

    epoch_sealing_task = getattr(app.state, "epoch_sealing_task", None)
    if epoch_sealing_task is not None:
        epoch_sealing_task.cancel()
        try:
            await epoch_sealing_task
        except asyncio.CancelledError:
            pass
        logger.info("Epoch sealing task stopped")

    projection_engine_task = getattr(app.state, "projection_engine_task", None)
    if projection_engine_task is not None:
        projection_engine_task.cancel()
        try:
            await projection_engine_task
        except asyncio.CancelledError:
            pass
        logger.info("Projection engine task stopped")

    connector_runner = getattr(app.state, "connector_runner", None)
    if connector_runner is not None:
        await connector_runner.stop_all()
        app.state.connector_runner = None
        logger.info("Connector runner stopped")

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
