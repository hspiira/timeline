"""Email provider protocols and data structures (provider-agnostic)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class EmailMessage:
    """Universal email message structure (provider-agnostic)."""

    message_id: str
    thread_id: str | None
    from_address: str
    to_addresses: list[str]
    subject: str
    timestamp: datetime
    labels: list[str]
    is_read: bool
    is_starred: bool
    has_attachments: bool
    provider_metadata: dict[str, Any]


@dataclass
class EmailProviderConfig:
    """Provider configuration and credentials."""

    provider_type: str  # gmail, outlook, imap
    email_address: str
    credentials: dict[str, Any]
    connection_params: dict[str, Any] = field(default_factory=dict)


class IEmailProvider(Protocol):
    """Universal email provider interface (DIP)."""

    async def connect(self, config: EmailProviderConfig) -> None:
        """Establish connection to email provider."""
        ...

    async def disconnect(self) -> None:
        """Close connection."""
        ...

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[EmailMessage]:
        """Fetch messages. since: only after this timestamp; limit: max count."""
        ...

    async def setup_webhook(self, callback_url: str) -> dict[str, Any]:
        """Setup webhook/push for real-time sync. Returns webhook config."""
        ...

    async def remove_webhook(self) -> None:
        """Remove webhook."""
        ...

    @property
    def supports_webhooks(self) -> bool:
        """Whether this provider supports webhooks."""
        ...

    @property
    def supports_incremental_sync(self) -> bool:
        """Whether this provider supports incremental sync."""
        ...
