"""Repository interfaces (ports) for the application layer.

Protocols define contracts that infrastructure implementations must fulfill (DIP).
All types reference application DTOs or schemas only; no infrastructure imports.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from app.domain.enums import TenantStatus

if TYPE_CHECKING:
    from app.application.dtos.document import DocumentCreate, DocumentResult
    from app.application.dtos.document_category import DocumentCategoryResult
    from app.application.dtos.event import EventCreate, EventResult, EventToPersist
    from app.application.dtos.event_schema import EventSchemaResult
    from app.application.dtos.permission import PermissionResult
    from app.application.dtos.role import RoleResult
    from app.application.dtos.search import SearchResultItem
    from app.application.dtos.subject import SubjectResult
    from app.application.dtos.subject_snapshot import SubjectSnapshotResult
    from app.application.dtos.subject_type import SubjectTypeResult
    from app.application.dtos.task import TaskResult
    from app.application.dtos.tenant import TenantResult
    from app.application.dtos.user import UserResult


# Event repository interface
class IEventRepository(Protocol):
    """Protocol for event repository (DIP)."""

    async def get_last_hash(self, subject_id: str, tenant_id: str) -> str | None:
        """Return hash of the most recent event for subject in tenant."""

    async def get_last_event(self, subject_id: str, tenant_id: str) -> EventResult | None:
        """Return the most recent event for subject in tenant."""

    async def get_last_events_for_subjects(
        self, tenant_id: str, subject_ids: set[str]
    ) -> dict[str, EventResult | None]:
        """Return the latest event per subject (batch). Missing subjects have None."""

    async def create_event(
        self,
        tenant_id: str,
        data: EventCreate,
        event_hash: str,
        previous_hash: str | None,
    ) -> EventResult:
        """Create a new event with computed hash."""

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list[EventToPersist],
    ) -> list[EventResult]:
        """Bulk insert events (hashes precomputed)."""

    async def get_by_id(self, event_id: str) -> EventResult | None:
        """Return event by ID."""

    async def get_by_subject(
        self, subject_id: str, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventResult]:
        """Return events for subject in tenant (newest first)."""

    async def get_events_chronological(
        self,
        subject_id: str,
        tenant_id: str,
        as_of: datetime | None = None,
        after_event_id: str | None = None,
        limit: int = 10000,
    ) -> list[EventResult]:
        """Return events for subject in chronological order (oldest first). If as_of is set, only events with event_time <= as_of. If after_event_id is set, only events after that event (for snapshot replay)."""

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return total event count for tenant (for verification limit check)."""

    async def get_counts_by_type(self, tenant_id: str) -> dict[str, int]:
        """Return event counts per event_type for tenant."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventResult]:
        """Return events for tenant with pagination (for verification)."""


# Subject repository interface
class ISubjectRepository(Protocol):
    """Protocol for subject repository (DIP)."""

    async def get_by_id(self, subject_id: str) -> SubjectResult | None:
        """Return subject by ID."""

    async def get_by_id_and_tenant(
        self, subject_id: str, tenant_id: str
    ) -> SubjectResult | None:
        """Return subject by ID if it belongs to tenant."""

    async def get_by_ids_and_tenant(
        self, tenant_id: str, subject_ids: set[str]
    ) -> list[SubjectResult]:
        """Return subjects for the given ids in this tenant (batch)."""

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return total subject count for tenant."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[SubjectResult]:
        """Return subjects for tenant with pagination."""

    async def get_counts_by_type(self, tenant_id: str) -> dict[str, int]:
        """Return subject counts per subject_type for tenant."""

    async def get_by_type(
        self,
        tenant_id: str,
        subject_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SubjectResult]:
        """Return subjects of type for tenant."""

    async def get_by_external_ref(
        self, tenant_id: str, external_ref: str
    ) -> SubjectResult | None:
        """Return subject by external reference."""

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
        display_name: str | None = None,
        attributes: dict | None = None,
    ) -> SubjectResult:
        """Create subject; return created entity."""

    async def update_subject(
        self,
        tenant_id: str,
        subject_id: str,
        external_ref: str | None = None,
        display_name: str | None = None,
        attributes: dict | None = None,
    ) -> SubjectResult | None:
        """Update subject; return updated result or None if not found in tenant."""

    async def delete_subject(
        self, tenant_id: str, subject_id: str
    ) -> bool:
        """Delete subject; return True if deleted, False if not found in tenant."""


# Subject snapshot repository interface
class ISubjectSnapshotRepository(Protocol):
    """Protocol for subject snapshot repository (DIP)."""

    async def get_latest_by_subject(
        self, subject_id: str, tenant_id: str
    ) -> SubjectSnapshotResult | None:
        """Return latest snapshot for subject in tenant, or None."""

    async def create_snapshot(
        self,
        subject_id: str,
        tenant_id: str,
        snapshot_at_event_id: str,
        state_json: dict,
        event_count_at_snapshot: int = 0,
    ) -> SubjectSnapshotResult:
        """Create or replace snapshot for subject (one per subject)."""


# Event schema repository interface
class IEventSchemaRepository(Protocol):
    """Protocol for event schema repository (DIP)."""

    async def get_by_id(self, schema_id: str) -> EventSchemaResult | None:
        """Return schema by ID."""

    async def get_by_version(
        self, tenant_id: str, event_type: str, version: int
    ) -> EventSchemaResult | None:
        """Return specific schema version."""

    async def get_active_schema(
        self, tenant_id: str, event_type: str
    ) -> EventSchemaResult | None:
        """Return active schema for event type and tenant."""

    async def get_all_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> list[EventSchemaResult]:
        """Return all schema versions for event type."""

    async def get_next_version(self, tenant_id: str, event_type: str) -> int:
        """Return next version number for event_type."""


# Subject type repository interface
class ISubjectTypeRepository(Protocol):
    """Protocol for subject type configuration repository (DIP)."""

    async def get_by_id(self, subject_type_id: str) -> SubjectTypeResult | None:
        """Return subject type by ID."""

    async def get_by_tenant_and_type(
        self, tenant_id: str, type_name: str
    ) -> SubjectTypeResult | None:
        """Return active subject type for tenant and type_name."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[SubjectTypeResult]:
        """Return subject types for tenant with pagination."""

    async def create_subject_type(
        self,
        tenant_id: str,
        type_name: str,
        display_name: str,
        *,
        description: str | None = None,
        schema: dict | None = None,
        is_active: bool = True,
        icon: str | None = None,
        color: str | None = None,
        has_timeline: bool = True,
        allow_documents: bool = True,
        created_by: str | None = None,
    ) -> SubjectTypeResult:
        """Create a subject type; return created entity."""

    async def update_subject_type(
        self,
        subject_type_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        schema: dict | None = None,
        is_active: bool | None = None,
        icon: str | None = None,
        color: str | None = None,
        has_timeline: bool | None = None,
        allow_documents: bool | None = None,
    ) -> SubjectTypeResult | None:
        """Update subject type; return updated result or None if not found."""

    async def delete_subject_type(
        self, subject_type_id: str, tenant_id: str
    ) -> bool:
        """Delete subject type; return True if deleted, False if not found."""


# Document category repository interface
class IDocumentCategoryRepository(Protocol):
    """Protocol for document category configuration repository (DIP)."""

    async def get_by_id(self, category_id: str) -> DocumentCategoryResult | None:
        """Return document category by ID."""

    async def get_by_tenant_and_name(
        self, tenant_id: str, category_name: str
    ) -> DocumentCategoryResult | None:
        """Return active document category for tenant and category_name."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[DocumentCategoryResult]:
        """Return document categories for tenant with pagination."""

    async def create_document_category(
        self,
        tenant_id: str,
        category_name: str,
        display_name: str,
        *,
        description: str | None = None,
        metadata_schema: dict | None = None,
        default_retention_days: int | None = None,
        is_active: bool = True,
    ) -> DocumentCategoryResult:
        """Create a document category; return created entity."""

    async def update_document_category(
        self,
        category_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        metadata_schema: dict | None = None,
        default_retention_days: int | None = None,
        is_active: bool | None = None,
    ) -> DocumentCategoryResult | None:
        """Update document category; return updated result or None if not found."""

    async def delete_document_category(
        self, category_id: str, tenant_id: str
    ) -> bool:
        """Delete document category; return True if deleted, False if not found."""


# Tenant repository interface
class ITenantRepository(Protocol):
    """Protocol for tenant repository (DIP). Postgres and Firestore implementations."""

    async def get_by_id(self, tenant_id: str) -> TenantResult | None:
        """Return tenant by ID."""

    async def get_by_code(self, code: str) -> TenantResult | None:
        """Return tenant by code."""

    async def create_tenant(
        self, code: str, name: str, status: TenantStatus
    ) -> TenantResult:
        """Create tenant; return created entity with id."""

    async def get_active_tenants(
        self, skip: int = 0, limit: int = 100
    ) -> list[TenantResult]:
        """Return active tenants with pagination."""

    async def update_tenant(
        self,
        tenant_id: str,
        name: str | None = None,
        status: TenantStatus | None = None,
    ) -> TenantResult | None:
        """Update tenant name and/or status; return updated result or None."""


# User repository interface
class IUserRepository(Protocol):
    """Protocol for user repository (DIP). Postgres and Firestore implementations."""

    async def get_by_id(self, user_id: str) -> UserResult | None:
        """Return user by ID."""

    async def get_by_id_and_tenant(
        self, user_id: str, tenant_id: str
    ) -> UserResult | None:
        """Return user by ID if they belong to the tenant."""

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> UserResult:
        """Create user with hashed password; return created user."""


# Document repository interface
class IDocumentRepository(Protocol):
    """Protocol for document repository (DIP)."""

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return count of non-deleted documents for tenant."""

    async def list_by_tenant(
        self,
        tenant_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        document_type: str | None = None,
        include_deleted: bool = False,
        created_before: datetime | None = None,
    ) -> list[DocumentResult]:
        """List documents for tenant (for retention job and admin)."""

    async def get_by_id(self, document_id: str) -> DocumentResult | None:
        """Return document by ID."""

    async def get_by_id_and_tenant(
        self, document_id: str, tenant_id: str
    ) -> DocumentResult | None:
        """Return document by ID if it belongs to the tenant; otherwise None."""

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[DocumentResult]:
        """Return documents for subject in tenant."""

    async def get_by_checksum(
        self, tenant_id: str, checksum: str
    ) -> DocumentResult | None:
        """Return document by tenant and checksum (for duplicate check)."""

    async def create_document(self, document: DocumentCreate) -> DocumentResult:
        """Create document from write-model DTO; return created read-model."""

    async def mark_parent_not_latest_if_current(
        self, parent_id: str, expected_version: int
    ) -> bool:
        """Set parent is_latest_version=False only if still current (optimistic lock). Returns True if updated."""

    async def update(self, document: DocumentResult) -> DocumentResult:
        """Update document (e.g. is_latest_version)."""

    async def soft_delete(
        self, document_id: str, tenant_id: str
    ) -> DocumentResult | None:
        """Soft-delete document by id; returns None if not found in tenant."""


# Role repository interface
class IRoleRepository(Protocol):
    """Protocol for role repository (DIP)."""

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> RoleResult | None:
        """Return role by code and tenant if it exists; otherwise None."""

    async def create_role(
        self,
        tenant_id: str,
        code: str,
        name: str,
        description: str | None = None,
        *,
        is_system: bool = False,
        is_active: bool = True,
    ) -> RoleResult:
        """Create a role; return created read-model DTO."""


# Permission repository interface
class IPermissionRead(Protocol):
    """Minimal protocol for permission lookup result (has id for assignment)."""

    id: str


# Permission repository interface
class IPermissionRepository(Protocol):
    """Protocol for permission repository (DIP)."""

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> PermissionResult | None:
        """Return permission by code and tenant if it exists; otherwise None."""

    async def create_permission(
        self,
        tenant_id: str,
        code: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> PermissionResult:
        """Create a permission; return created entity."""


# Role permission repository interface
class IRolePermissionRepository(Protocol):
    """Protocol for role-permission assignment repository (DIP)."""

    async def assign_permission_to_role(
        self, role_id: str, permission_id: str, tenant_id: str
    ) -> None:
        """Assign a permission to a role in the tenant. Raises DuplicateAssignmentException if already assigned."""


# Task repository interface (workflow create_task action)
class ITaskRepository(Protocol):
    """Protocol for task repository (workflow-created tasks)."""

    async def create(
        self,
        tenant_id: str,
        subject_id: str,
        event_id: str | None,
        title: str,
        *,
        assigned_to_role_id: str | None = None,
        assigned_to_user_id: str | None = None,
        due_at: datetime | None = None,
        status: str = "open",
        description: str | None = None,
    ) -> "TaskResult":
        """Create a task; return created result. At least one of assigned_to_role_id or assigned_to_user_id recommended."""


# Search repository interface (full-text search)
class ISearchRepository(Protocol):
    """Protocol for full-text search across subjects, events, and optionally documents."""

    async def full_text_search(
        self,
        tenant_id: str,
        q: str,
        scope: str = "all",
        limit: int = 50,
    ) -> list["SearchResultItem"]:
        """Search within tenant. scope: all | subjects | events | documents. Returns ranked results."""


# Audit log repository interface (append-only)
if TYPE_CHECKING:
    from app.application.dtos.audit_log import AuditLogEntryCreate, AuditLogResult


class IAuditLogRepository(Protocol):
    """Protocol for API audit log repository (DIP). Append-only."""

    async def create(self, entry: "AuditLogEntryCreate") -> "AuditLogResult":
        """Append one audit log entry; return created record."""

    async def list(
        self,
        tenant_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        resource_type: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ) -> list["AuditLogResult"]:
        """List audit log entries for tenant with optional filters (paginated)."""
