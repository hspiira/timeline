"""Connector framework: ingest events from external systems (CDC, Kafka, email, files).

Connectors implement IConnector; ConnectorRunner runs them in-process and
publishes via EventService. See docs/PLATFORM_VISION_AND_ROADMAP.md.
"""

from app.connectors.base import (
    ConnectorEvent,
    ConnectorHealth,
    IConnector,
)
from app.connectors.runner import ConnectorRunner

__all__ = [
    "ConnectorEvent",
    "ConnectorHealth",
    "IConnector",
    "ConnectorRunner",
]
