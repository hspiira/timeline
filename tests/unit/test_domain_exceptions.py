"""Tests for domain exceptions (error_code, message, details)."""

import pytest

from app.domain.exceptions import (
    AuthenticationException,
    AuthorizationException,
    CredentialException,
    DocumentVersionConflictException,
    DuplicateAssignmentException,
    DuplicateEmailException,
    EventChainBrokenException,
    ResourceNotFoundException,
    SchemaValidationException,
    SqlNotConfiguredException,
    TenantAlreadyExistsException,
    TenantNotFoundException,
    TimelineException,
    TransitionValidationException,
    UserAlreadyExistsException,
    ValidationException,
    VerificationLimitExceededException,
)


def test_timeline_exception_default_error_code() -> None:
    """Base TimelineException uses class name as error_code when not provided."""
    exc = TimelineException("Something failed")
    assert exc.message == "Something failed"
    assert exc.error_code == "TimelineException"
    assert exc.details == {}


def test_timeline_exception_custom_error_code_and_details() -> None:
    """TimelineException accepts custom error_code and details."""
    exc = TimelineException("Oops", error_code="CUSTOM", details={"key": "value"})
    assert exc.message == "Oops"
    assert exc.error_code == "CUSTOM"
    assert exc.details == {"key": "value"}


def test_validation_exception() -> None:
    """ValidationException sets VALIDATION_ERROR and optional field in details."""
    exc = ValidationException("Invalid format", field="email")
    assert exc.message == "Invalid format"
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details == {"field": "email"}


def test_validation_exception_without_field() -> None:
    """ValidationException with no field has empty details."""
    exc = ValidationException("Invalid")
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details == {}


def test_authentication_exception() -> None:
    """AuthenticationException sets AUTHENTICATION_ERROR and default message."""
    exc = AuthenticationException()
    assert exc.message == "Authentication failed"
    assert exc.error_code == "AUTHENTICATION_ERROR"


def test_authentication_exception_custom_message() -> None:
    exc = AuthenticationException("Invalid token")
    assert exc.message == "Invalid token"
    assert exc.error_code == "AUTHENTICATION_ERROR"


def test_authorization_exception_default() -> None:
    """AuthorizationException with no resource/action uses default message."""
    exc = AuthorizationException()
    assert exc.message == "Permission denied"
    assert exc.error_code == "PERMISSION_DENIED"
    assert exc.details == {}


def test_authorization_exception_with_resource_and_action() -> None:
    """AuthorizationException with resource and action builds message and details."""
    exc = AuthorizationException(resource="event", action="create")
    assert exc.message == "Permission denied: create on event"
    assert exc.error_code == "PERMISSION_DENIED"
    assert exc.details == {"resource": "event", "action": "create"}


def test_tenant_not_found_exception() -> None:
    exc = TenantNotFoundException("t-123")
    assert "t-123" in exc.message
    assert exc.error_code == "TENANT_NOT_FOUND"
    assert exc.details == {"tenant_id": "t-123"}


def test_tenant_already_exists_exception() -> None:
    exc = TenantAlreadyExistsException("acme")
    assert "acme" in exc.message
    assert exc.error_code == "TENANT_ALREADY_EXISTS"
    assert exc.details == {"code": "acme"}


def test_user_already_exists_exception() -> None:
    exc = UserAlreadyExistsException()
    assert "already registered" in exc.message
    assert exc.error_code == "USER_ALREADY_EXISTS"
    assert exc.details == {}


def test_duplicate_email_exception() -> None:
    exc = DuplicateEmailException()
    assert "already registered" in exc.message
    assert exc.error_code == "DUPLICATE_EMAIL"


def test_document_version_conflict_exception() -> None:
    exc = DocumentVersionConflictException("doc-1")
    assert "retry" in exc.message
    assert exc.error_code == "DOCUMENT_VERSION_CONFLICT"
    assert exc.details == {"parent_document_id": "doc-1"}


def test_resource_not_found_exception() -> None:
    exc = ResourceNotFoundException("subject", "sub-456")
    assert "subject" in exc.message and "sub-456" in exc.message
    assert exc.error_code == "RESOURCE_NOT_FOUND"
    assert exc.details == {"resource_type": "subject", "resource_id": "sub-456"}


def test_event_chain_broken_exception() -> None:
    exc = EventChainBrokenException("sub-1", "ev-1", "hash mismatch")
    assert "sub-1" in exc.message
    assert exc.error_code == "CHAIN_INTEGRITY_ERROR"
    assert exc.details == {
        "subject_id": "sub-1",
        "event_id": "ev-1",
        "reason": "hash mismatch",
    }


def test_verification_limit_exceeded_exception() -> None:
    exc = VerificationLimitExceededException("t-1", 50_000, 10_000)
    assert "50" in exc.message and "10" in exc.message
    assert exc.error_code == "VERIFICATION_LIMIT_EXCEEDED"
    assert exc.details == {
        "tenant_id": "t-1",
        "total_events": 50_000,
        "max_events": 10_000,
    }


def test_schema_validation_exception() -> None:
    errors = [{"path": ["x"], "msg": "required"}]
    exc = SchemaValidationException("status_changed", errors)
    assert "status_changed" in exc.message
    assert exc.error_code == "SCHEMA_VALIDATION_ERROR"
    assert exc.details == {"schema_type": "status_changed", "errors": errors}


def test_sql_not_configured_exception() -> None:
    exc = SqlNotConfiguredException()
    assert "SQL" in exc.message
    assert exc.error_code == "SERVICE_UNAVAILABLE"


def test_credential_exception() -> None:
    exc = CredentialException("Decryption failed")
    assert exc.message == "Decryption failed"
    assert exc.error_code == "CREDENTIAL_ERROR"


def test_transition_validation_exception() -> None:
    exc = TransitionValidationException(
        "Missing prior type",
        event_type="updated",
        required_prior_event_types=["created"],
        reason="missing",
    )
    assert exc.message == "Missing prior type"
    assert exc.error_code == "TRANSITION_VIOLATION"
    assert exc.details["event_type"] == "updated"
    assert exc.details["required_prior_event_types"] == ["created"]
    assert exc.details["reason"] == "missing"


def test_duplicate_assignment_exception() -> None:
    exc = DuplicateAssignmentException(
        "Permission already assigned",
        assignment_type="role_permission",
        details_extra={"role_id": "r1", "permission_id": "p1"},
    )
    assert "already assigned" in exc.message
    assert exc.error_code == "DUPLICATE_ASSIGNMENT"
    assert exc.details["assignment_type"] == "role_permission"
    assert exc.details["role_id"] == "r1"
    assert exc.details["permission_id"] == "p1"


def test_exception_is_raiseable() -> None:
    """All exceptions can be raised and caught as TimelineException."""
    with pytest.raises(TimelineException) as exc_info:
        raise ValidationException("Bad input", field="x")
    assert exc_info.value.error_code == "VALIDATION_ERROR"
