"""Repository interfaces (ports) for the application layer.

Protocols define contracts that infrastructure implementations must fulfill (DIP).
All types reference application DTOs or schemas only; no infrastructure imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.domain.enums import TenantStatus

if TYPE_CHECKING:
    from app.application.dtos.document import DocumentCreate, DocumentResult
    from app.application.dtos.event import CreateEventCommand, EventResult, EventToPersist
    from app.application.dtos.event_schema import EventSchemaResult
    from app.application.dtos.role import RoleResult
    from app.application.dtos.subject import SubjectResult
    from app.application.dtos.tenant import TenantResult
    from app.application.dtos.user import UserResult


class IEventRepository(Protocol):
    """Protocol for event repository (DIP)."""

    async def get_last_hash(self, subject_id: str, tenant_id: str) -> str | None:
        """Return hash of the most recent event for subject in tenant."""
        ...

    async def get_last_event(self, subject_id: str, tenant_id: str) -> EventResult | None:
        """Return the most recent event for subject in tenant."""
        ...

    async def get_last_events_for_subjects(
        self, tenant_id: str, subject_ids: set[str]
    ) -> dict[str, EventResult | None]:
        """Return the latest event per subject (batch). Missing subjects have None."""
        ...

    async def create_event(
        self,
        tenant_id: str,
        data: CreateEventCommand,
        event_hash: str,
        previous_hash: str | None,
    ) -> EventResult:
        """Create a new event with computed hash."""
        ...

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list[EventToPersist],
    ) -> list[EventResult]:
        """Bulk insert events (hashes precomputed)."""
        ...

    async def get_by_id(self, event_id: str) -> EventResult | None:
        """Return event by ID."""
        ...

    async def get_by_subject(
        self, subject_id: str, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventResult]:
        """Return events for subject in tenant (newest first)."""
        ...

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return total event count for tenant (for verification limit check)."""
        ...

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventResult]:
        """Return events for tenant with pagination (for verification)."""
        ...


class ISubjectRepository(Protocol):
    """Protocol for subject repository (DIP)."""

    async def get_by_id(self, subject_id: str) -> SubjectResult | None:
        """Return subject by ID."""
        ...

    async def get_by_id_and_tenant(
        self, subject_id: str, tenant_id: str
    ) -> SubjectResult | None:
        """Return subject by ID if it belongs to tenant."""
        ...

    async def get_by_ids_and_tenant(
        self, tenant_id: str, subject_ids: set[str]
    ) -> list[SubjectResult]:
        """Return subjects for the given ids in this tenant (batch)."""
        ...

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[SubjectResult]:
        """Return subjects for tenant with pagination."""
        ...

    async def get_by_type(
        self,
        tenant_id: str,
        subject_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SubjectResult]:
        """Return subjects of type for tenant."""
        ...

    async def get_by_external_ref(
        self, tenant_id: str, external_ref: str
    ) -> SubjectResult | None:
        """Return subject by external reference."""
        ...

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
    ) -> SubjectResult:
        """Create subject; return created entity."""
        ...

    async def update_subject(
        self,
        tenant_id: str,
        subject_id: str,
        external_ref: str | None = None,
    ) -> SubjectResult | None:
        """Update subject; return updated result or None if not found in tenant."""
        ...

    async def delete_subject(
        self, tenant_id: str, subject_id: str
    ) -> bool:
        """Delete subject; return True if deleted, False if not found in tenant."""
        ...


class IEventSchemaRepository(Protocol):
    """Protocol for event schema repository (DIP)."""

    async def get_by_id(self, schema_id: str) -> EventSchemaResult | None:
        """Return schema by ID."""
        ...

    async def get_by_version(
        self, tenant_id: str, event_type: str, version: int
    ) -> EventSchemaResult | None:
        """Return specific schema version."""
        ...

    async def get_active_schema(
        self, tenant_id: str, event_type: str
    ) -> EventSchemaResult | None:
        """Return active schema for event type and tenant."""
        ...

    async def get_all_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> list[EventSchemaResult]:
        """Return all schema versions for event type."""
        ...

    async def get_next_version(self, tenant_id: str, event_type: str) -> int:
        """Return next version number for event_type."""
        ...


class ITenantRepository(Protocol):
    """Protocol for tenant repository (DIP). Postgres and Firestore implementations."""

    async def get_by_id(self, tenant_id: str) -> TenantResult | None:
        """Return tenant by ID."""
        ...

    async def get_by_code(self, code: str) -> TenantResult | None:
        """Return tenant by code."""
        ...

    async def create_tenant(
        self, code: str, name: str, status: TenantStatus
    ) -> TenantResult:
        """Create tenant; return created entity with id."""
        ...

    async def get_active_tenants(
        self, skip: int = 0, limit: int = 100
    ) -> list[TenantResult]:
        """Return active tenants with pagination."""
        ...

    async def update_tenant(
        self,
        tenant_id: str,
        name: str | None = None,
        status: TenantStatus | None = None,
    ) -> TenantResult | None:
        """Update tenant name and/or status; return updated result or None."""
        ...


class IUserRepository(Protocol):
    """Protocol for user repository (DIP). Postgres and Firestore implementations."""

    async def get_by_id(self, user_id: str) -> UserResult | None:
        """Return user by ID."""
        ...

    async def get_by_id_and_tenant(
        self, user_id: str, tenant_id: str
    ) -> UserResult | None:
        """Return user by ID if they belong to the tenant."""
        ...

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> UserResult:
        """Create user with hashed password; return created user."""
        ...


class IDocumentRepository(Protocol):
    """Protocol for document repository (DIP)."""

    async def get_by_id(self, document_id: str) -> DocumentResult | None:
        """Return document by ID."""
        ...

    async def get_by_id_and_tenant(
        self, document_id: str, tenant_id: str
    ) -> DocumentResult | None:
        """Return document by ID if it belongs to the tenant; otherwise None."""
        ...

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[DocumentResult]:
        """Return documents for subject in tenant."""
        ...

    async def get_by_checksum(
        self, tenant_id: str, checksum: str
    ) -> DocumentResult | None:
        """Return document by tenant and checksum (for duplicate check)."""
        ...

    async def create_document(self, document: DocumentCreate) -> DocumentResult:
        """Create document from write-model DTO; return created read-model."""
        ...

    async def mark_parent_not_latest_if_current(
        self, parent_id: str, expected_version: int
    ) -> bool:
        """Set parent is_latest_version=False only if still current (optimistic lock). Returns True if updated."""
        ...

    async def update(self, document: DocumentResult) -> DocumentResult:
        """Update document (e.g. is_latest_version)."""
        ...

    async def soft_delete(
        self, document_id: str, tenant_id: str
    ) -> DocumentResult | None:
        """Soft-delete document by id; returns None if not found in tenant."""
        ...


class IRoleRepository(Protocol):
    """Protocol for role repository (DIP)."""

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> RoleResult | None:
        """Return role by code and tenant if it exists; otherwise None."""
        ...

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
        ...


class IPermissionRead(Protocol):
    """Minimal protocol for permission lookup result (has id for assignment)."""

    id: str


class IPermissionRepository(Protocol):
    """Protocol for permission repository (DIP)."""

    async def get_by_code_and_tenant(
        self, code: str, tenant_id: str
    ) -> PermissionResult | None:
        """Return permission by code and tenant if it exists; otherwise None."""
        ...

    async def create_permission(
        self,
        tenant_id: str,
        code: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> PermissionResult:
        """Create a permission; return created entity."""
        ...


class IRolePermissionRepository(Protocol):
    """Protocol for role-permission assignment repository (DIP)."""

    async def assign_permission_to_role(
        self, role_id: str, permission_id: str, tenant_id: str
    ) -> None:
        """Assign a permission to a role in the tenant. Raises DuplicateAssignmentException if already assigned."""
        ...
