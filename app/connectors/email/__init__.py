"""Email ingestion connector (wraps existing email infrastructure)."""

from app.connectors.email.connector import EmailConnector

__all__ = ["EmailConnector"]
