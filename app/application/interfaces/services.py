"""Service interfaces (ports) for the application layer.

Protocols define contracts for application services (DIP).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from app.shared.enums import ActorType, AuditAction

if TYPE_CHECKING:
    from app.application.dtos.event import EventCreate
    from app.domain.entities.event import EventEntity


# Hash service interface
class IHashService(Protocol):
    """Protocol for hash computation (event chain integrity)."""

    def compute_hash(
        self,
        subject_id: str,
        event_type: str,
        schema_version: int,
        event_time: datetime,
        payload: dict[str, Any],
        previous_hash: str | None,
    ) -> str:
        """Compute hash for event data (canonical JSON + previous_hash)."""


# Event transition validator interface
class IEventTransitionValidator(Protocol):
    """Protocol for validating that required prior event types exist before emitting an event type."""

    async def validate_can_emit(
        self,
        tenant_id: str,
        subject_id: str,
        event_type: str,
        workflow_instance_id: str | None = None,
    ) -> None:
        """Raise TransitionValidationException if rules exist and required prior event types are missing in the stream."""


# Event schema validator interface
class IEventSchemaValidator(Protocol):
    """Protocol for validating event payload against tenant schema (single responsibility)."""

    async def validate_payload(
        self,
        tenant_id: str,
        event_type: str,
        schema_version: int,
        payload: dict[str, Any],
        subject_type: str | None = None,
    ) -> None:
        """Validate payload against tenant schema (version).

        When subject_type is provided and schema has allowed_subject_types,
        subject_type must be in that list. Raises TimelineException subclass
        when the schema is not found, inactive, or validation fails.
        """


# Event service interface
class IEventService(Protocol):
    """Protocol for event creation use case."""

    async def create_event(
        self,
        tenant_id: str,
        data: EventCreate,
        *,
        trigger_workflows: bool = True,
    ) -> EventEntity:
        """Create a new event with cryptographic chaining and optional schema validation."""

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list[EventCreate],
        *,
        skip_schema_validation: bool = False,
        trigger_workflows: bool = False,
    ) -> list[EventEntity]:
        """Bulk create events (e.g. email sync)."""


# Workflow engine interface
class IWorkflowEngine(Protocol):
    """Protocol for workflow execution triggered by events."""

    async def process_event_triggers(self, event: Any, tenant_id: str) -> list[Any]:
        """Find and execute workflows for event; return executions."""


# Notification service interface (workflow notify action)
class INotificationService(Protocol):
    """Protocol for sending notifications (e.g. email) to a list of recipients."""

    async def send(
        self,
        to_emails: list[str],
        subject: str,
        body: str,
    ) -> None:
        """Send notification (e.g. email) to the given addresses. No-op or log if not configured."""


# Workflow recipient resolver: resolve user emails by role code (for notify action)
class IWorkflowRecipientResolver(Protocol):
    """Protocol for resolving notification recipients by tenant and role code."""

    async def get_emails_for_role(self, tenant_id: str, role_code: str) -> list[str]:
        """Return list of email addresses for users who have the given role in the tenant."""


# Tenant initialization service interface
class ITenantInitializationService(Protocol):
    """Protocol for initializing new tenant RBAC and audit infrastructure."""

    async def initialize_tenant_infrastructure(self, tenant_id: str) -> None:
        """Create permissions, roles, role-permissions, audit schema and subject."""

    async def assign_admin_role(self, tenant_id: str, admin_user_id: str) -> None:
        """Assign admin role to user (call after user creation)."""


# Permission resolver interface
class IPermissionResolver(Protocol):
    """Protocol for resolving user permissions (used by AuthorizationService)."""

    async def get_user_permissions(self, user_id: str, tenant_id: str) -> set[str]:
        """Return set of permission codes (e.g. {'event:create', 'subject:read'})."""


# Audit service interface
class IAuditService(Protocol):
    """Protocol for emitting system audit events."""

    async def emit_audit_event(
        self,
        tenant_id: str,
        entity_type: str,
        action: AuditAction,
        entity_id: str,
        entity_data: dict[str, Any],
        actor_id: str | None = None,
        actor_type: ActorType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit one audit event."""


# API audit log service interface (general audit log table, not event store)
class IApiAuditLogService(Protocol):
    """Protocol for logging API actions to audit_log table (SOC 2)."""

    async def log_action(
        self,
        tenant_id: str,
        user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Append one audit log entry (who did what, when, to which resource)."""


# Cache service interface
class ICacheService(Protocol):
    """Minimal cache protocol for permission caching (DIP)."""

    def is_available(self) -> bool:
        """Return True if cache is connected."""

    async def get(self, key: str) -> Any:
        """Return cached value or None."""

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Store value with TTL. Returns True on success."""

    async def delete(self, key: str) -> bool:
        """Delete key. Returns True on success."""

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern. Returns count deleted."""
