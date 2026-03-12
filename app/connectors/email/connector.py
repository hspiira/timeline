"""Email connector: polls email accounts and yields events (stub until full sync)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime

from app.connectors.base import ConnectorEvent, ConnectorHealth, ConnectorStatus

logger = logging.getLogger(__name__)


class EmailConnector:
    """IConnector that polls for email-derived events.

    When connector_email_enabled and connector_email_tenant_id are set, this
    connector runs in the runner. Currently yields empty batches on a poll
    interval; full sync (fetch messages via Gmail/IMAP, map to ConnectorEvent)
    is planned to replace the stub loop.
    """

    def __init__(
        self,
        connector_id: str,
        tenant_id: str,
        *,
        poll_interval_seconds: float = 60.0,
    ) -> None:
        self._connector_id = connector_id
        self._tenant_id = tenant_id
        self._poll_interval_seconds = poll_interval_seconds
        self._running = False
        self._stop_event = asyncio.Event()
        self._last_event_at: datetime | None = None
        self._error: str | None = None

    @property
    def connector_id(self) -> str:
        return self._connector_id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    async def start(self) -> None:
        """Mark connector as running (no external connection yet)."""
        self._running = True
        self._stop_event.clear()
        self._error = None
        logger.info("Email connector %s started for tenant %s", self._connector_id, self._tenant_id)

    async def stop(self) -> None:
        """Mark connector as stopped."""
        self._running = False
        self._stop_event.set()
        logger.info("Email connector %s stopped", self._connector_id)

    async def health(self) -> ConnectorHealth:
        """Return current health (running/stopped; no lag until real sync)."""
        status = ConnectorStatus.RUNNING if self._running else ConnectorStatus.STOPPED
        return ConnectorHealth(
            connector_id=self._connector_id,
            status=status,
            last_event_at=self._last_event_at,
            error=self._error,
            lag=None,
        )

    def events(self) -> AsyncIterator[list[ConnectorEvent]]:
        """Yield batches of events. Stub: yields empty list on poll interval until stopped."""
        async def _generate() -> AsyncIterator[list[ConnectorEvent]]:
            while self._running:
                # Stub: no email fetch yet; yield empty batch. Replace with:
                # - load email accounts for tenant (sync_status=pending or periodic poll)
                # - fetch messages via provider, map to ConnectorEvent, yield batches
                yield []
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._poll_interval_seconds,
                    )
                except asyncio.TimeoutError:
                    continue

        return _generate()
