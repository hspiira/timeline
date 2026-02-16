"""Domain exceptions for the Timeline application.

Defines domain-level exceptions that represent business rule violations.
These exceptions are independent of infrastructure concerns. Presentation
layer maps them to HTTP responses in exception handlers.
"""

from typing import Any


class TimelineException(Exception):
    """Base exception for all Timeline application errors.

    All custom exceptions should inherit from this class to allow
    consistent error handling and logging. Presentation layer maps
    these to HTTP responses using message, error_code, and details.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code.
        details: Additional error context (e.g. field, resource_id).
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description.
            error_code: Optional machine-readable code; defaults to class name.
            details: Optional dict of extra context.
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(TimelineException):
    """Raised when input validation fails (e.g. invalid format or range)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize with message and optional field name.

        Args:
            message: Description of the validation failure.
            field: Optional field or attribute that failed validation.
        """
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationException(TimelineException):
    """Raised when authentication fails (e.g. invalid credentials or token)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize with optional message.

        Args:
            message: Description of the authentication failure.
        """
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationException(TimelineException):
    """Raised when the user lacks required permissions for the operation."""

    def __init__(
        self,
        resource: str | None = None,
        action: str | None = None,
        message: str = "Permission denied",
    ) -> None:
        """Initialize with optional resource, action, and message.

        Args:
            resource: Optional resource type (e.g. 'event', 'subject').
            action: Optional action that was attempted (e.g. 'create', 'read').
            message: Human-readable message; default used when resource/action omitted.
        """
        if resource and action:
            message = f"Permission denied: {action} on {resource}"
        details: dict[str, Any] = {}
        if resource:
            details["resource"] = resource
        if action:
            details["action"] = action
        super().__init__(message, "PERMISSION_DENIED", details)


class TenantNotFoundException(TimelineException):
    """Raised when a requested tenant is not found."""

    def __init__(self, tenant_id: str) -> None:
        """Initialize with the missing tenant identifier.

        Args:
            tenant_id: The tenant ID that was not found.
        """
        super().__init__(
            f"Tenant not found: {tenant_id}",
            "TENANT_NOT_FOUND",
            {"tenant_id": tenant_id},
        )


class TenantAlreadyExistsException(TimelineException):
    """Raised when creating a tenant whose code already exists."""

    def __init__(self, code: str) -> None:
        """Initialize with the duplicate tenant code.

        Args:
            code: The tenant code that already exists.
        """
        super().__init__(
            f"Tenant with code '{code}' already exists",
            "TENANT_ALREADY_EXISTS",
            {"code": code},
        )


class UserAlreadyExistsException(TimelineException):
    """Raised when creating a user whose username or email already exists in the tenant."""

    def __init__(self) -> None:
        """Initialize with a generic message (username/email duplicate in tenant)."""
        super().__init__(
            "Username or email already registered in this tenant",
            "USER_ALREADY_EXISTS",
            {},
        )


class DuplicateEmailException(TimelineException):
    """Raised when updating a user to an email already registered in the tenant."""

    def __init__(self) -> None:
        """Initialize with a generic message (email duplicate in tenant)."""
        super().__init__(
            "Email is already registered in this tenant",
            "DUPLICATE_EMAIL",
            {},
        )


class DocumentVersionConflictException(TimelineException):
    """Raised when a concurrent request won the parent version update (optimistic lock)."""

    def __init__(self, parent_document_id: str) -> None:
        super().__init__(
            "Document was updated by another request; retry.",
            "DOCUMENT_VERSION_CONFLICT",
            {"parent_document_id": parent_document_id},
        )


class ResourceNotFoundException(TimelineException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize with resource type and id.

        Args:
            resource_type: Type of resource (e.g. 'subject', 'event').
            resource_id: The ID that was not found.
        """
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            "RESOURCE_NOT_FOUND",
            {"resource_type": resource_type, "resource_id": resource_id},
        )


class EventChainBrokenException(TimelineException):
    """Raised when event chain integrity is violated (e.g. hash mismatch)."""

    def __init__(self, subject_id: str, event_id: str, reason: str) -> None:
        """Initialize with subject, event, and reason.

        Args:
            subject_id: Subject whose chain is broken.
            event_id: Event where the break was detected.
            reason: Human-readable reason (e.g. 'hash mismatch').
        """
        super().__init__(
            f"Event chain broken for subject {subject_id}",
            "CHAIN_INTEGRITY_ERROR",
            {"subject_id": subject_id, "event_id": event_id, "reason": reason},
        )


class VerificationLimitExceededException(TimelineException):
    """Raised when tenant event count exceeds verification_max_events (use background job)."""

    def __init__(self, tenant_id: str, total_events: int, max_events: int) -> None:
        """Initialize with tenant and counts.

        Args:
            tenant_id: Tenant whose event count exceeded the limit.
            total_events: Current total event count.
            max_events: Configured maximum for inline verification.
        """
        super().__init__(
            f"Tenant has {total_events} events; maximum for inline verification is {max_events}",
            "VERIFICATION_LIMIT_EXCEEDED",
            {"tenant_id": tenant_id, "total_events": total_events, "max_events": max_events},
        )


class SchemaValidationException(TimelineException):
    """Raised when event payload fails schema validation."""

    def __init__(self, schema_type: str, validation_errors: list[Any]) -> None:
        """Initialize with schema type and validation errors.

        Args:
            schema_type: Event type or schema identifier.
            validation_errors: List of validation error details (e.g. from jsonschema).
        """
        super().__init__(
            f"Schema validation failed for {schema_type}",
            "SCHEMA_VALIDATION_ERROR",
            {"schema_type": schema_type, "errors": validation_errors},
        )


class SqlNotConfiguredException(TimelineException):
    """Raised when an operation requires Postgres but the backend is not configured."""

    def __init__(self) -> None:
        super().__init__(
            message="This operation requires a SQL database that is not configured.",
            error_code="SERVICE_UNAVAILABLE",
        )


class CredentialException(TimelineException):
    """Raised when credential decryption or format fails (e.g. OAuth client secrets)."""

    def __init__(self, message: str = "Credential operation failed") -> None:
        super().__init__(message, "CREDENTIAL_ERROR")


class TransitionValidationException(TimelineException):
    """Raised when an event type is emitted without required prior event types in the stream."""

    def __init__(
        self,
        message: str,
        event_type: str,
        required_prior_event_types: list[str],
        **details_extra: Any,
    ) -> None:
        """Initialize with message and transition context.

        Args:
            message: Human-readable description.
            event_type: The event type that was rejected.
            required_prior_event_types: Event types that must have occurred first.
            **details_extra: Optional keys merged into details (e.g. reason, max).
        """
        details = {
            "event_type": event_type,
            "required_prior_event_types": required_prior_event_types,
            **details_extra,
        }
        super().__init__(message, "TRANSITION_VIOLATION", details)


class DuplicateAssignmentException(TimelineException):
    """Raised when assigning a role/permission that is already assigned (unique constraint)."""

    def __init__(self, message: str, assignment_type: str, details_extra: dict[str, Any] | None = None) -> None:
        """Initialize with message and assignment context.

        Args:
            message: Human-readable description (e.g. 'Permission already assigned to role').
            assignment_type: 'role_permission' or 'user_role'.
            details_extra: Optional extra keys (e.g. role_id, permission_id).
        """
        details = details_extra or {}
        details["assignment_type"] = assignment_type
        super().__init__(message, "DUPLICATE_ASSIGNMENT", details)
