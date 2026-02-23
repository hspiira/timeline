"""Email account API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Allowed values for sync_status (PATCH and responses).
EmailAccountSyncStatus = Literal["idle", "pending", "syncing", "error"]


class EmailAccountCreateRequest(BaseModel):
    """Request body for creating an email account."""

    subject_id: str = Field(..., min_length=1)
    provider_type: str = Field(..., min_length=1, description="e.g. gmail, outlook, imap")
    email_address: EmailStr = Field(...)
    credentials: dict = Field(default_factory=dict, description="Provider credentials (encrypted at rest)")
    connection_params: dict | None = None
    oauth_provider_config_id: str | None = None


class EmailAccountUpdate(BaseModel):
    """Request body for PATCH (partial update)."""

    email_address: EmailStr | None = None
    connection_params: dict | None = None
    is_active: bool | None = None
    sync_status: EmailAccountSyncStatus | None = None


class EmailAccountSyncStatusResponse(BaseModel):
    """Response for GET sync-status: last sync time, status, error."""

    account_id: str
    sync_status: str
    last_sync_at: datetime | None = None
    sync_started_at: datetime | None = None
    sync_completed_at: datetime | None = None
    sync_error: str | None = None
    sync_messages_fetched: int = 0
    sync_events_created: int = 0


class EmailSyncAcceptedResponse(BaseModel):
    """Response for POST sync / sync-background (202 Accepted)."""

    detail: str
    account_id: str


class WebhookAckResponse(BaseModel):
    """Response for POST webhook (202 Accepted)."""

    detail: str = "Webhook received"
    account_id: str


class EmailAccountResponse(BaseModel):
    """Response model for list and detail email account endpoints (consistent fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    subject_id: str
    provider_type: str
    email_address: str
    is_active: bool
    sync_status: str
    last_sync_at: datetime | None
    oauth_status: str | None = None
