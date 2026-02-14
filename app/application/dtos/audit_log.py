"""DTOs for audit log (API action log)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AuditLogEntryCreate:
    """Input for appending one audit log record. Append-only; no update."""

    tenant_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    success: bool
    error_message: str | None


@dataclass(frozen=True)
class AuditLogResult:
    """Single audit log entry (read-model for list/get)."""

    id: str
    tenant_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    timestamp: datetime
    success: bool
    error_message: str | None
