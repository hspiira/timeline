"""Pydantic schemas for webhook subscription API."""

from datetime import datetime

from pydantic import BaseModel, Field


class WebhookSubscriptionCreateRequest(BaseModel):
    """Request body for creating a webhook subscription."""

    target_url: str = Field(..., description="URL to receive POST requests")
    event_types: list[str] = Field(
        default_factory=list,
        description="Event types to deliver (empty = all)",
    )
    subject_types: list[str] = Field(
        default_factory=list,
        description="Subject types to deliver (empty = all)",
    )
    secret: str = Field(..., description="Secret for HMAC-SHA256 signature verification")


class WebhookSubscriptionUpdateRequest(BaseModel):
    """Request body for PATCH (all optional)."""

    target_url: str | None = None
    event_types: list[str] | None = None
    subject_types: list[str] | None = None
    secret: str | None = None
    active: bool | None = None


class WebhookSubscriptionResponse(BaseModel):
    """Webhook subscription in list/detail (secret never included)."""

    id: str
    tenant_id: str
    target_url: str
    event_types: list[str]
    subject_types: list[str]
    active: bool
    created_at: datetime


class WebhookSubscriptionCreateResponse(WebhookSubscriptionResponse):
    """Response for create; includes secret once for client to verify signatures."""

    secret: str = Field(..., description="Stored secret; only returned on create")


class WebhookSubscriptionTestResponse(BaseModel):
    """Response for test delivery."""

    delivered: bool = Field(..., description="True if target returned 2xx")
