"""Connector protocol and DTOs for platform event ingestion.

Connectors produce ConnectorEvent batches; the runner maps them to EventCreate
and calls EventService. Health is reported per connector for admin endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Protocol


class ConnectorStatus(str, Enum):
    """Connector lifecycle status for health reporting."""

    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"


@dataclass
class ConnectorEvent:
    """Single event produced by a connector (maps to EventCreate with external_id/source)."""

    subject_id: str
    subject_type: str
    event_type: str
    event_time: datetime
    payload: dict[str, Any]
    external_id: str
    source: str
    schema_version: int = 1
    correlation_id: str | None = None
    workflow_instance_id: str | None = None


@dataclass
class ConnectorHealth:
    """Health status for one connector (admin/operational)."""

    connector_id: str
    status: ConnectorStatus
    last_event_at: datetime | None
    error: str | None = None
    lag: int | None = None


class IConnector(Protocol):
    """Protocol for event connectors: start, stop, health, and event stream."""

    @property
    def connector_id(self) -> str:
        """Unique identifier for this connector instance."""
        ...

    @property
    def tenant_id(self) -> str:
        """Tenant all produced events belong to."""
        ...

    async def start(self) -> None:
        """Establish connection to source; call before events()."""
        ...

    async def stop(self) -> None:
        """Release connection; call on shutdown or error."""
        ...

    async def health(self) -> ConnectorHealth:
        """Current health for this connector."""
        ...

    def events(self) -> AsyncIterator[list[ConnectorEvent]]:
        """Yield batches of events; caller is responsible for ack/offset advancement."""
        ...
