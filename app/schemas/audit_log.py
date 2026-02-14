"""Request/response schemas for audit log API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogEntryResponse(BaseModel):
    """Single audit log entry (read)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    timestamp: datetime
    success: bool
    error_message: str | None = None


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditLogEntryResponse]
    skip: int
    limit: int
