"""Domain exceptions for the Timeline application.

Defines domain-level exceptions that represent business rule violations.
These exceptions are independent of infrastructure concerns. Presentation
layer maps them to HTTP responses in exception handlers.
"""

from typing import Any


class TimelineException(Exception):
    """Base exception for all Timeline application errors.

    All custom exceptions should inherit from this class to allow
    consistent error handling and logging. Handlers can use to_dict()
    for API responses.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code for API responses.
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
            details: Optional dict of extra context for the response.
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses.

        Returns:
            Dict with keys: error, message, details.
        """
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


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

    def __init__(self, resource: str, action: str) -> None:
        """Initialize with resource and action that was denied.

        Args:
            resource: Resource type (e.g. 'event', 'subject').
            action: Action that was attempted (e.g. 'create', 'read').
        """
        message = f"Permission denied: {action} on {resource}"
        super().__init__(message, "AUTHORIZATION_ERROR", {"resource": resource, "action": action})


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


class PermissionDeniedError(TimelineException):
    """Raised when the user lacks a required permission."""

    def __init__(
        self,
        message: str = "Permission denied",
        resource: str | None = None,
        action: str | None = None,
    ) -> None:
        """Initialize with optional message and context.

        Args:
            message: Optional custom message.
            resource: Optional resource that was denied.
            action: Optional action that was denied.
        """
        details: dict[str, Any] = {}
        if resource:
            details["resource"] = resource
        if action:
            details["action"] = action
        super().__init__(message, "PERMISSION_DENIED", details)
