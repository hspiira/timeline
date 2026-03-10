"""Connector registry: maps connector_type string to connector class.

Used when connectors are configured from DB (connector_mapping or similar);
allows runtime resolution of connector class from type name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from app.connectors.base import IConnector

# Populate when implementing CDC/Kafka/email/file_watch connectors.
_CONNECTOR_CLASSES: dict[str, Type[IConnector]] = {}


def register_connector_type(connector_type: str, cls: Type[IConnector]) -> None:
    """Register a connector class for the given type name."""
    _CONNECTOR_CLASSES[connector_type] = cls


def get_connector_class(connector_type: str) -> Type[IConnector] | None:
    """Return the connector class for the given type, or None if unknown."""
    return _CONNECTOR_CLASSES.get(connector_type)
