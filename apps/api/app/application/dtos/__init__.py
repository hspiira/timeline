"""Application DTOs (no ORM dependency)."""

from app.application.dtos.document import (
    DocumentCreate,
    DocumentListItem,
    DocumentMetadata,
    DocumentResult,
)
from app.application.dtos.event import EventCreate, EventResult, EventToPersist
from app.application.dtos.event_schema import EventSchemaResult
from app.application.dtos.permission import PermissionResult
from app.application.dtos.role import RoleResult
from app.application.dtos.state import StateResult
from app.application.dtos.subject import SubjectResult
from app.application.dtos.tenant import TenantCreationResult, TenantResult
from app.application.dtos.user import UserResult

__all__ = [
    "EventCreate",
    "DocumentCreate",
    "DocumentListItem",
    "DocumentMetadata",
    "DocumentResult",
    "EventResult",
    "EventSchemaResult",
    "EventToPersist",
    "PermissionResult",
    "RoleResult",
    "StateResult",
    "SubjectResult",
    "TenantCreationResult",
    "TenantResult",
    "UserResult",
]
