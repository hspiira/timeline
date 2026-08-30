"""Pydantic schemas for webhook subscription API."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.application.validators.webhook_url import validate_webhook_target_url


def _validate_target_url(v: str) -> str:
    """Reject SSRF-unsafe webhook URLs (loopback, link-local, private)."""
    validate_webhook_target_url(v)
    return v


class WebhookSubscriptionCreateRequest(BaseModel):
    """Request body for creating a webhook subscription."""

    target_url: HttpUrl = Field(..., description="URL to receive POST requests")
    event_types: list[str] = Field(
        default_factory=list,
        description="Event types to deliver (empty = all)",
    )
    subject_types: list[str] = Field(
        default_factory=list,
        description="Subject types to deliver (empty = all)",
    )
    secret: str = Field(
        ...,
        min_length=16,
        description="Secret for HMAC-SHA256 signature verification (min 16 chars)",
    )

    @field_validator("target_url")
    @classmethod
    def target_url_safe(cls, v: HttpUrl) -> HttpUrl:
        _validate_target_url(str(v))
        return v


class WebhookSubscriptionUpdateRequest(BaseModel):
    """Request body for PATCH (all optional)."""

    target_url: HttpUrl | None = None
    event_types: list[str] | None = None
    subject_types: list[str] | None = None
    secret: str | None = None
    active: bool | None = None

    @field_validator("target_url")
    @classmethod
    def target_url_safe(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None:
            _validate_target_url(str(v))
        return v


class WebhookSubscriptionResponse(BaseModel):
    """Webhook subscription in list/detail (secret never included)."""

    id: str
    tenant_id: str
    target_url: str
    event_types: list[str]
    subject_types: list[str]
    secret_present: bool = Field(
        ..., description="True if a signing secret is configured (value never returned)"
    )
    active: bool
    created_at: datetime


class WebhookSubscriptionCreateResponse(WebhookSubscriptionResponse):
    """Response for create; includes secret once for client to verify signatures."""

    secret: str = Field(..., description="Stored secret; only returned on create")


class WebhookSubscriptionTestResponse(BaseModel):
    """Response for test delivery."""

    delivered: bool = Field(..., description="True if target returned 2xx")
