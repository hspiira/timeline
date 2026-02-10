"""Shared enumerations for the Timeline application.

Cross-cutting enums used by application and infrastructure (e.g. audit,
actor type, workflow). Domain-specific enums (e.g. TenantStatus) live
in app.domain.enums.
"""

from enum import Enum


class _ValuesMixin:
    """Mixin that adds a values() classmethod to str Enums."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid values as strings."""
        return [member.value for member in cls]


class ActorType(_ValuesMixin, str, Enum):
    """Actor type for event and audit tracking (who performed the action)."""

    USER = "user"
    SYSTEM = "system"
    EXTERNAL = "external"


class DocumentAccessLevel(_ValuesMixin, str, Enum):
    """Document access level for storage and authorization."""

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class OAuthStatus(_ValuesMixin, str, Enum):
    """OAuth account / token status."""

    ACTIVE = "active"
    CONSENT_DENIED = "consent_denied"
    REFRESH_FAILED = "refresh_failed"
    REVOKED = "revoked"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class WorkflowExecutionStatus(_ValuesMixin, str, Enum):
    """Workflow execution lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditAction(_ValuesMixin, str, Enum):
    """Audit action types for system event tracking."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
