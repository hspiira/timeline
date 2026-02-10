"""Repository interfaces (ports) for the application layer.

Protocols define contracts that infrastructure implementations must fulfill (DIP).
Use TYPE_CHECKING for model/schema types so application has no runtime infra deps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from app.application.dtos.event import EventToPersist
    from app.infrastructure.persistence.models.event import Event
    from app.infrastructure.persistence.models.event_schema import EventSchema
    from app.infrastructure.persistence.models.subject import Subject
    from app.infrastructure.persistence.models.tenant import Tenant
    from app.infrastructure.persistence.models.user import User
    from app.schemas.event import EventCreate


class IEventRepository(Protocol):
    """Protocol for event repository (DIP)."""

    async def get_last_hash(self, subject_id: str, tenant_id: str) -> str | None:
        """Return hash of the most recent event for subject in tenant."""
        ...

    async def get_last_event(self, subject_id: str, tenant_id: str) -> "Event | None":
        """Return the most recent event for subject in tenant."""
        ...

    async def create_event(
        self,
        tenant_id: str,
        data: "EventCreate",
        event_hash: str,
        previous_hash: str | None,
    ) -> "Event":
        """Create a new event with computed hash."""
        ...

    async def create_events_bulk(
        self,
        tenant_id: str,
        events: list["EventToPersist"],
    ) -> list["Event"]:
        """Bulk insert events (hashes precomputed)."""
        ...

    async def get_by_id(self, event_id: str) -> "Event | None":
        """Return event by ID."""
        ...

    async def get_by_subject(
        self, subject_id: str, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list["Event"]:
        """Return events for subject in tenant (newest first)."""
        ...

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list["Event"]:
        """Return events for tenant with pagination (for verification)."""
        ...


class ISubjectRepository(Protocol):
    """Protocol for subject repository (DIP)."""

    async def get_by_id(self, subject_id: str) -> "Subject | None":
        """Return subject by ID."""
        ...

    async def get_by_id_and_tenant(
        self, subject_id: str, tenant_id: str
    ) -> "Subject | None":
        """Return subject by ID if it belongs to tenant."""
        ...

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list["Subject"]:
        """Return subjects for tenant with pagination."""
        ...

    async def get_by_type(
        self,
        tenant_id: str,
        subject_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list["Subject"]:
        """Return subjects of type for tenant."""
        ...

    async def get_by_external_ref(
        self, tenant_id: str, external_ref: str
    ) -> "Subject | None":
        """Return subject by external reference."""
        ...

    async def create_subject(
        self,
        tenant_id: str,
        subject_type: str,
        external_ref: str | None = None,
    ) -> "Subject":
        """Create subject; return created entity."""
        ...


class IEventSchemaRepository(Protocol):
    """Protocol for event schema repository (DIP)."""

    async def get_by_id(self, schema_id: str) -> "EventSchema | None":
        """Return schema by ID."""
        ...

    async def get_by_version(
        self, tenant_id: str, event_type: str, version: int
    ) -> "EventSchema | None":
        """Return specific schema version."""
        ...

    async def get_active_schema(
        self, tenant_id: str, event_type: str
    ) -> "EventSchema | None":
        """Return active schema for event type and tenant."""
        ...

    async def get_all_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> list["EventSchema"]:
        """Return all schema versions for event type."""
        ...

    async def get_next_version(self, tenant_id: str, event_type: str) -> int:
        """Return next version number for event_type."""
        ...


class ITenantRepository(Protocol):
    """Protocol for tenant repository (DIP)."""

    async def get_by_id(self, tenant_id: str) -> "Tenant | None":
        """Return tenant by ID."""
        ...

    async def get_by_code(self, code: str) -> "Tenant | None":
        """Return tenant by code."""
        ...

    async def create_tenant(self, code: str, name: str, status: str) -> "Tenant":
        """Create tenant; return created entity with id."""
        ...


class IUserRepository(Protocol):
    """Protocol for user repository (DIP)."""

    async def get_by_id(self, user_id: str) -> "User | None":
        """Return user by ID."""
        ...

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
    ) -> "User":
        """Create user with hashed password; return created user."""
        ...


class IDocumentRepository(Protocol):
    """Protocol for document repository (DIP)."""

    async def get_by_id(self, document_id: str) -> Any:
        """Return document by ID."""
        ...

    async def get_by_subject(
        self,
        subject_id: str,
        tenant_id: str,
        include_deleted: bool = False,
    ) -> Any:
        """Return documents for subject in tenant."""
        ...

    async def get_by_checksum(self, tenant_id: str, checksum: str) -> Any:
        """Return document by tenant and checksum (for duplicate check)."""
        ...

    async def create(self, document: Any) -> Any:
        """Create document; return created entity."""
        ...

    async def update(self, document: Any) -> Any:
        """Update document (e.g. is_latest_version)."""
        ...
