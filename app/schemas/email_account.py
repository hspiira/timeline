"""Email account API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
