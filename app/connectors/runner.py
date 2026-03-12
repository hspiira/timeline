"""ConnectorRunner: lifecycle and ingestion for IConnector instances."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING, Callable

from app.application.dtos.event import EventCreate
from app.connectors.base import ConnectorEvent, ConnectorHealth, IConnector

if TYPE_CHECKING:
    from app.application.use_cases.events import EventService
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class ConnectorRunner:
    """Runs connectors in-process; ingests batches via EventService."""

    def __init__(
        self,
        event_service_factory: Callable[
            [str], AbstractAsyncContextManager["EventService"]
        ],
    ) -> None:
        """Initialize runner with a factory that yields EventService per tenant_id."""
        self._event_service_factory = event_service_factory
        self._connectors: list[IConnector] = []
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def register(self, connector: IConnector) -> None:
        """Register a connector to run (call before start_all)."""
        if any(c.connector_id == connector.connector_id for c in self._connectors):
            raise ValueError(f"Duplicate connector_id: {connector.connector_id}")
        self._connectors.append(connector)

    async def start_all(self) -> None:
        """Start all registered connectors as background tasks."""
        if self._tasks:
            raise RuntimeError("ConnectorRunner is already running")
        for connector in self._connectors:
            task = asyncio.create_task(
                self._run_connector(connector),
                name=f"connector:{connector.connector_id}",
            )
            self._tasks[connector.connector_id] = task
        logger.info("ConnectorRunner started %d connector(s)", len(self._connectors))

    async def stop_all(self) -> None:
        """Cancel all connector tasks and wait for them to finish."""
        for task in self._tasks.values():
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
            self._tasks.clear()
        logger.info("ConnectorRunner stopped all connectors")

    async def all_health(self) -> list[ConnectorHealth]:
        """Return health for all registered connectors."""
        return [await c.health() for c in self._connectors]

    async def _run_connector(self, connector: IConnector) -> None:
        """Run one connector: start, consume events(), ingest; restart on crash with backoff."""
        backoff_seconds = 5
        max_backoff = 300
        while True:
            try:
                await connector.start()
                it: AsyncIterator[list[ConnectorEvent]] = connector.events()
                try:
                    async for batch in it:
                        await self._ingest_batch(connector, batch)
                    return  # clean exit
                finally:
                    await connector.stop()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Connector %s crashed, restarting in %ds",
                    connector.connector_id,
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff)

    async def _ingest_batch(
        self, connector: IConnector, batch: list[ConnectorEvent]
    ) -> None:
        """Map batch to EventCreate and call EventService.create_event per event."""
        async with self._event_service_factory(connector.tenant_id) as event_service:
            for event in batch:
                try:
                    create_data = EventCreate(
                        subject_id=event.subject_id,
                        event_type=event.event_type,
                        schema_version=event.schema_version,
                        event_time=event.event_time,
                        payload=event.payload,
                        external_id=event.external_id,
                        source=event.source,
                        correlation_id=event.correlation_id,
                        workflow_instance_id=event.workflow_instance_id,
                    )
                    await event_service.create_event(
                        connector.tenant_id,
                        create_data,
                        trigger_workflows=False,
                        skip_transition_validation=True,
                        skip_schema_validation=True,
                    )
                except Exception:
                    logger.exception(
                        "Connector %s failed to ingest event %s",
                        connector.connector_id,
                        event.external_id,
                    )


def make_event_service_factory(
    session_factory: "async_sessionmaker[AsyncSession]",
    app: object | None = None,
) -> Callable[[str], AbstractAsyncContextManager["EventService"]]:
    """Build an async context manager factory that yields EventService per tenant_id.

    Used by lifespan to create ConnectorRunner's event_service_factory.
    When app is provided, connector-ingested events trigger webhooks and SSE.
    """
    from app.api.v1.dependencies._domain import build_event_service_for_connector

    @asynccontextmanager
    async def factory(tenant_id: str):
        async with session_factory() as db:
            yield build_event_service_for_connector(db, tenant_id, app=app)

    return factory
