"""Domain layer: entities, value objects, enums, and exceptions.

No dependencies on infrastructure or presentation. Used by application
and infrastructure layers.
"""

from app.domain.entities import (
    EventEntity,
    EventSchemaEntity,
    SubjectEntity,
    TenantEntity,
)
from app.domain.enums import TenantStatus
from app.domain.exceptions import (
    AuthenticationException,
    AuthorizationException,
    CredentialException,
    DuplicateAssignmentException,
    EventChainBrokenException,
    ResourceNotFoundException,
    SchemaValidationException,
    SqlNotConfiguredException,
    TenantNotFoundException,
    TimelineException,
    TransitionValidationException,
    ValidationException,
    VerificationLimitExceededException,
)
from app.domain.value_objects import (
    EventChain,
    EventType,
    Hash,
    SubjectType,
    TenantCode,
)

__all__ = [
    "AuthenticationException",
    "AuthorizationException",
    "CredentialException",
    "SqlNotConfiguredException",
    "DuplicateAssignmentException",
    "EventChain",
    "EventChainBrokenException",
    "EventEntity",
    "EventSchemaEntity",
    "EventType",
    "Hash",
    "ResourceNotFoundException",
    "SchemaValidationException",
    "SubjectEntity",
    "SubjectType",
    "TenantCode",
    "TenantEntity",
    "TenantNotFoundException",
    "TenantStatus",
    "TimelineException",
    "TransitionValidationException",
    "ValidationException",
    "VerificationLimitExceededException",
]
