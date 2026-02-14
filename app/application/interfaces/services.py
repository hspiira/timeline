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


# Event schema validator interface
class IEventSchemaValidator(Protocol):
    """Protocol for validating event payload against tenant schema (single responsibility)."""

    async def validate_payload(
        self,
        tenant_id: str,
        event_type: str,
        schema_version: int,
        payload: dict[str, Any],
    ) -> None:
        """Raise ValueError if schema not found, inactive, or payload invalid."""


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
