"""DTOs for webhook subscription."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WebhookSubscriptionResult:
    """Read model for a webhook subscription."""

    id: str
    tenant_id: str
    target_url: str
    event_types: list[str]
    subject_types: list[str]
    secret: str
    active: bool
    created_at: datetime


@dataclass
class WebhookSubscriptionCreate:
    """Input for creating a webhook subscription."""

    target_url: str
    event_types: list[str]
    subject_types: list[str]
    secret: str


@dataclass
class WebhookSubscriptionUpdate:
    """Input for patching a webhook subscription (all optional)."""

    target_url: str | None = None
    event_types: list[str] | None = None
    subject_types: list[str] | None = None
    secret: str | None = None
    active: bool | None = None
