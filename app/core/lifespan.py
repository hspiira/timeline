"""Application lifespan: startup and shutdown.

Single place for all startup/shutdown logic (SRP). Used by main.py;
no business logic here, only wiring of infrastructure (cache,
WebSocket manager, telemetry, DB engine dispose).

Imports of subsystems stay inside the functions that wire them. That is
deliberate: it keeps import-time side effects out of module import, which is what
lets "python -c 'from app.main import app'" stay a cheap check in CI.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Coroutine

import httpx
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.verification_job_store import VerificationJobStore

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _BackgroundJob:
    """One optional background job: whether it runs, and how to start it."""

    enabled: bool
    attr: str
    label: str
    task_name: str
    make_coro: Callable[[FastAPI], Coroutine[Any, Any, Any]]


def _projection_engine_coro(app: FastAPI) -> Coroutine[Any, Any, Any]:
    from app.core.projection_engine_job import run_projection_engine_job

    return run_projection_engine_job(app)


def _chain_anchor_coro(app: FastAPI) -> Coroutine[Any, Any, Any]:
    from app.core.anchor_job import run_chain_anchor_job

    return run_chain_anchor_job(app)


def _epoch_sealing_coro(app: FastAPI) -> Coroutine[Any, Any, Any]:
    from app.core.epoch_sealing_job import run_epoch_sealing_job
    from app.infrastructure.persistence.database import AsyncSessionLocal

    return run_epoch_sealing_job(
        app.state.oauth_http_client,
        AsyncSessionLocal,
        get_settings(),
    )


def _tsa_batch_coro(app: FastAPI) -> Coroutine[Any, Any, Any]:
    from app.core.tsa_batch_job import run_tsa_batch_job

    return run_tsa_batch_job(app)


def _background_jobs(settings: "Settings") -> list[_BackgroundJob]:
    """The optional background jobs, in start order."""
    return [
        _BackgroundJob(
            enabled=settings.projection_engine_enabled,
            attr="projection_engine_task",
            label="Projection engine",
            task_name="projection_engine",
            make_coro=_projection_engine_coro,
        ),
        _BackgroundJob(
            enabled=settings.chain_anchor_enabled,
            attr="chain_anchor_task",
            label="Chain anchor job",
            task_name="chain_anchor",
            make_coro=_chain_anchor_coro,
        ),
        _BackgroundJob(
            enabled=settings.epoch_sealing_enabled,
            attr="epoch_sealing_task",
            label="Epoch sealing job",
            task_name="epoch_sealing",
            make_coro=_epoch_sealing_coro,
        ),
        _BackgroundJob(
            enabled=settings.tsa_batch_enabled,
            attr="tsa_batch_task",
            label="TSA batch job",
            task_name="tsa_batch",
            make_coro=_tsa_batch_coro,
        ),
    ]


def _start_background_jobs(app: FastAPI, settings: "Settings") -> None:
    """Start each enabled job; record None for the rest so shutdown can read them all."""
    for job in _background_jobs(settings):
        if not job.enabled:
            setattr(app.state, job.attr, None)
            continue
        task = asyncio.create_task(job.make_coro(app), name=job.task_name)
        setattr(app.state, job.attr, task)
        logger.info("%s started", job.label)


async def _cancel_background_task(app: FastAPI, attr: str, label: str) -> None:
    """Cancel one background task recorded on app.state and wait for it to unwind."""
    task = getattr(app.state, attr, None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("%s stopped", label)


async def _start_event_streaming(app: FastAPI, settings: "Settings") -> None:
    """Wire cache, rate limiter, and event stream. Falls back to in-memory without Redis."""
    from app.infrastructure.services.event_stream_broadcaster import (
        InMemoryEventStreamBroadcaster,
    )

    if not settings.redis_enabled:
        app.state.cache = None
        app.state.event_rate_limiter = None
        app.state.sync_progress_broadcast_task = None
        app.state.event_stream_broadcaster = InMemoryEventStreamBroadcaster()
        return

    from app.infrastructure.cache.redis_cache import CacheService
    from app.infrastructure.messaging.event_publisher import RedisEventPublisher
    from app.infrastructure.messaging.redis_pubsub import run_sync_progress_broadcast
    from app.infrastructure.services.redis_rate_limiter import RedisRateLimiter

    cache = CacheService()
    await cache.connect()
    app.state.cache = cache
    app.state.event_rate_limiter = RedisRateLimiter(cache.redis) if cache.redis else None
    app.state.event_stream_broadcaster = (
        RedisEventPublisher(cache.redis)
        if cache.redis is not None
        else InMemoryEventStreamBroadcaster()
    )
    app.state.sync_progress_broadcast_task = asyncio.create_task(
        run_sync_progress_broadcast(app)
    )


async def _start_connectors(app: FastAPI, settings: "Settings") -> None:
    """Start the connector runner when any connector is enabled and a database exists."""
    app.state.connector_runner = None
    app.state.connector_runner_task = None

    enabled = (
        settings.connector_cdc_postgres_enabled
        or settings.connector_kafka_enabled
        or settings.connector_email_enabled
        or settings.connector_file_watch_enabled
    )
    if not enabled:
        return

    from app.infrastructure.persistence.database import AsyncSessionLocal

    if AsyncSessionLocal is None:
        logger.warning(
            "Connectors enabled but database not configured; connector runner disabled"
        )
        return

    from app.connectors.runner import ConnectorRunner, make_event_service_factory

    factory = make_event_service_factory(AsyncSessionLocal, app)
    runner = ConnectorRunner(event_service_factory=factory)
    _register_connectors(runner, settings)
    app.state.connector_runner = runner
    await runner.start_all()
    logger.info("Connector runner started")


def _register_connectors(runner: Any, settings: "Settings") -> None:
    """Register the implemented connectors. CDC, Kafka, and file_watch are pending."""
    if settings.connector_email_enabled and settings.connector_email_tenant_id:
        from app.connectors.email.connector import EmailConnector

        runner.register(
            EmailConnector(
                connector_id="email",
                tenant_id=settings.connector_email_tenant_id,
                poll_interval_seconds=settings.connector_email_poll_interval_seconds,
            )
        )


def _start_telemetry(app: FastAPI, settings: "Settings") -> None:
    """Configure and install telemetry when enabled."""
    if not settings.telemetry_enabled:
        return

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


async def _startup(app: FastAPI, settings: "Settings") -> None:
    """Wire everything the application needs, in dependency order."""
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

    await _start_event_streaming(app, settings)

    from app.projections import register_all_handlers

    register_all_handlers()

    # Started after the event stream: the jobs publish through it.
    _start_background_jobs(app, settings)
    await _start_connectors(app, settings)
    _start_telemetry(app, settings)


async def _shutdown(app: FastAPI) -> None:
    """Reverse the wiring. Order matters: tasks stop before what they depend on."""
    if getattr(app.state, "oauth_http_client", None) is not None:
        await app.state.oauth_http_client.aclose()
        app.state.oauth_http_client = None
        logger.info("OAuth HTTP client closed")

    await _cancel_background_task(app, "chain_anchor_task", "Chain anchor task")
    await _cancel_background_task(app, "tsa_batch_task", "TSA batch task")
    await _cancel_background_task(app, "epoch_sealing_task", "Epoch sealing task")
    await _cancel_background_task(app, "projection_engine_task", "Projection engine task")

    connector_runner = getattr(app.state, "connector_runner", None)
    if connector_runner is not None:
        await connector_runner.stop_all()
        app.state.connector_runner = None
        logger.info("Connector runner stopped")

    await _cancel_background_task(
        app, "sync_progress_broadcast_task", "Sync progress broadcast task"
    )
    await _close_infrastructure(app)


async def _close_infrastructure(app: FastAPI) -> None:
    """Release the connections the tasks were using, once none of them are running."""
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


@asynccontextmanager
async def create_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup then yield; on exit run shutdown.

    Startup order: shared HTTP client, WebSocket manager, storage, verification job
    store, event streaming (Redis cache when enabled), projection handlers, background
    jobs, connectors, telemetry. Shutdown reverses it: HTTP client, background jobs,
    connector runner, sync broadcast, cache, telemetry, SQL engine dispose.
    """
    settings = get_settings()
    await _startup(app, settings)
    yield
    await _shutdown(app)
