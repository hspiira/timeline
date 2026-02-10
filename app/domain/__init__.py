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
    EventChainBrokenException,
    PermissionDeniedError,
    ResourceNotFoundException,
    SchemaValidationException,
    TenantNotFoundException,
    TimelineException,
    ValidationException,
)
from app.domain.value_objects import (
    EventChain,
    EventType,
    Hash,
    SubjectType,
    TenantCode,
)

__all__ = [
    # Entities
    "EventEntity",
    "EventSchemaEntity",
    "SubjectEntity",
    "TenantEntity",
    # Enums
    "TenantStatus",
    # Exceptions
    "AuthenticationException",
    "AuthorizationException",
    "EventChainBrokenException",
    "PermissionDeniedError",
    "ResourceNotFoundException",
    "SchemaValidationException",
    "TenantNotFoundException",
    "TimelineException",
    "ValidationException",
    # Value objects
    "EventChain",
    "EventType",
    "Hash",
    "SubjectType",
    "TenantCode",
]
