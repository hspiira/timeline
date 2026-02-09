"""Shared enumerations for the Timeline application.

Cross-cutting enums used by application and infrastructure (e.g. audit,
actor type, workflow). Domain-specific enums (e.g. TenantStatus) live
in app.domain.enums.
"""

from enum import Enum


class ActorType(str, Enum):
    """Actor type for event and audit tracking (who performed the action)."""

    USER = "user"
    SYSTEM = "system"
    EXTERNAL = "external"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid values as strings."""
        return [actor.value for actor in cls]


class DocumentAccessLevel(str, Enum):
    """Document access level for storage and authorization."""

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid values as strings."""
        return [level.value for level in cls]


class OAuthStatus(str, Enum):
    """OAuth account / token status."""

    ACTIVE = "active"
    CONSENT_DENIED = "consent_denied"
    REFRESH_FAILED = "refresh_failed"
    REVOKED = "revoked"
    EXPIRED = "expired"
    UNKNOWN = "unknown"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid values as strings."""
        return [status.value for status in cls]


class WorkflowExecutionStatus(str, Enum):
    """Workflow execution lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid values as strings."""
        return [status.value for status in cls]


class AuditAction(str, Enum):
    """Audit action types for system event tracking."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid values as strings."""
        return [action.value for action in cls]
