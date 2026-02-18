"""Repository interfaces (ports) for the application layer.

Protocols define contracts that infrastructure implementations must fulfill (DIP).
All types reference application DTOs or schemas only; no infrastructure imports.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from app.domain.enums import TenantStatus

if TYPE_CHECKING:
    from app.application.dtos.audit_log import AuditLogEntryCreate, AuditLogResult
    from app.application.dtos.document import DocumentCreate, DocumentResult
    from app.application.dtos.document_requirement import (
        DocumentComplianceItem,
        DocumentRequirementResult,
        FlowDocumentComplianceResult,
    )
    from app.application.dtos.document_category import DocumentCategoryResult
    from app.application.dtos.event import EventCreate, EventResult, EventToPersist
    from app.application.dtos.flow import FlowResult, FlowSubjectResult
    from app.application.dtos.event_schema import EventSchemaResult
    from app.application.dtos.naming_template import NamingTemplateResult
    from app.application.dtos.event_transition_rule import EventTransitionRuleResult
    from app.application.dtos.permission import PermissionResult
    from app.application.dtos.role import RoleResult
    from app.application.dtos.search import SearchResultItem
    from app.application.dtos.relationship_kind import RelationshipKindResult
    from app.application.dtos.subject import SubjectResult
    from app.application.dtos.subject_relationship import SubjectRelationshipResult
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
        workflow_instance_id: str | None = None,
        limit: int = 10000,
    ) -> list[EventResult]:
        """Return events for subject in chronological order (oldest first). If as_of is set, only events with event_time <= as_of. If after_event_id is set, only events after that event (for snapshot replay). If workflow_instance_id is set, only events in that stream."""

    async def count_by_tenant(self, tenant_id: str) -> int:
        """Return total event count for tenant (for verification limit check)."""

    async def get_counts_by_type(self, tenant_id: str) -> dict[str, int]:
        """Return event counts per event_type for tenant."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventResult]:
        """Return events for tenant with pagination (for verification)."""

    async def get_by_workflow_instance_id(
        self,
        tenant_id: str,
        workflow_instance_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventResult]:
        """Return events for a flow (workflow_instance_id) across all subjects, newest first."""


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


# Relationship kind repository interface
class IRelationshipKindRepository(Protocol):
    """Protocol for relationship kind repository (DIP)."""

    async def list_by_tenant(
        self, tenant_id: str
    ) -> list[RelationshipKindResult]:
        """Return all configured relationship kinds for the tenant."""

    async def get_by_id(
        self, kind_id: str
    ) -> RelationshipKindResult | None:
        """Return relationship kind by ID."""

    async def get_by_tenant_and_kind(
        self, tenant_id: str, kind: str
    ) -> RelationshipKindResult | None:
        """Return relationship kind by tenant and kind string."""

    async def create(
        self,
        tenant_id: str,
        kind: str,
        display_name: str,
        description: str | None = None,
        payload_schema: dict | None = None,
    ) -> RelationshipKindResult:
        """Create a relationship kind; raise if duplicate kind for tenant."""

    async def update(
        self,
        kind_id: str,
        tenant_id: str,
        display_name: str | None = None,
        description: str | None = None,
        payload_schema: dict | None = None,
    ) -> RelationshipKindResult | None:
        """Update relationship kind; return None if not found or wrong tenant."""

    async def delete(self, kind_id: str, tenant_id: str) -> bool:
        """Delete relationship kind; return True if deleted."""


# Subject relationship repository interface
class ISubjectRelationshipRepository(Protocol):
    """Protocol for subject relationship repository (DIP)."""

    async def create(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
        payload: dict | None = None,
    ) -> SubjectRelationshipResult:
        """Create a relationship; raise if duplicate or subject not found."""

    async def delete(
        self,
        tenant_id: str,
        source_subject_id: str,
        target_subject_id: str,
        relationship_kind: str,
    ) -> bool:
        """Delete relationship; return True if deleted, False if not found."""

    async def list_for_subject(
        self,
        tenant_id: str,
        subject_id: str,
        *,
        as_source: bool = True,
        as_target: bool = True,
        relationship_kind: str | None = None,
    ) -> list[SubjectRelationshipResult]:
        """List relationships where subject is source and/or target, optional kind filter."""


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

    async def get_entity_by_id(self, schema_id: str) -> object | None:
        """Return ORM entity by id for update/delete."""

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

    async def get_all_for_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventSchemaResult]:
        """Return all event schemas for the tenant (any event type)."""

    async def get_next_version(self, tenant_id: str, event_type: str) -> int:
        """Return next version number for event_type."""

    async def create_schema(
        self,
        tenant_id: str,
        event_type: str,
        schema_definition: dict[str, Any],
        is_active: bool = True,
        allowed_subject_types: list[str] | None = None,
        created_by: str | None = None,
    ) -> EventSchemaResult:
        """Create event schema with next version; return created result."""

    async def update(
        self, obj: object, *, skip_existence_check: bool = False
    ) -> object:
        """Update existing schema (ORM); return updated entity."""

    async def delete(self, obj: object) -> None:
        """Delete schema (ORM)."""


# Event transition rule repository interface
class IEventTransitionRuleRepository(Protocol):
    """Protocol for event transition rule repository (DIP)."""

    async def get_by_id(self, rule_id: str) -> EventTransitionRuleResult | None:
        """Return rule by id."""

    async def get_by_id_and_tenant(
        self, rule_id: str, tenant_id: str
    ) -> EventTransitionRuleResult | None:
        """Return rule by id if it belongs to tenant."""

    async def get_rule_for_event_type(
        self, tenant_id: str, event_type: str
    ) -> EventTransitionRuleResult | None:
        """Return the transition rule for (tenant_id, event_type), or None."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[EventTransitionRuleResult]:
        """Return all transition rules for tenant."""

    async def get_entity_by_id(self, rule_id: str) -> object:
        """Return ORM entity by id for update/delete."""

    async def create_rule(
        self,
        tenant_id: str,
        event_type: str,
        required_prior_event_types: list[str],
        description: str | None = None,
        prior_event_payload_conditions: dict | None = None,
        max_occurrences_per_stream: int | None = None,
        fresh_prior_event_type: str | None = None,
    ) -> EventTransitionRuleResult:
        """Create a transition rule."""

    async def update(self, obj: object, *, skip_existence_check: bool = False) -> object:
        """Update rule."""

    async def delete(self, obj: object) -> None:
        """Delete rule."""


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
        allowed_event_types: list[str] | None = None,
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
        allowed_event_types: list[str] | None = None,
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


# Document requirement repository interface
class IDocumentRequirementRepository(Protocol):
    """Protocol for document requirement repository (required docs per workflow/step)."""

    async def get_by_workflow(
        self,
        tenant_id: str,
        workflow_id: str,
        step_definition_id: str | None = None,
    ) -> list["DocumentRequirementResult"]:
        """Return document requirements for workflow (and optional step)."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list["DocumentRequirementResult"]:
        """Return document requirements for tenant."""

    async def create(
        self,
        tenant_id: str,
        workflow_id: str,
        document_category_id: str,
        min_count: int = 1,
        step_definition_id: str | None = None,
    ) -> "DocumentRequirementResult":
        """Create a document requirement."""

    async def delete(self, requirement_id: str, tenant_id: str) -> bool:
        """Delete document requirement; return True if deleted."""


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

    async def update_password(self, user_id: str, new_password: str) -> UserResult | None:
        """Update user password by id; return updated user or None if not found."""


# Password set token store (one-time token for C2 set-initial-password flow)
class IPasswordSetTokenStore(Protocol):
    """One-time token for setting initial admin password. Create at tenant creation; redeem at set-password."""

    async def create(self, user_id: str) -> tuple[str, datetime]:
        """Create a one-time token for user; return (raw_token, expires_at)."""

    async def redeem(self, token: str) -> str | None:
        """If token is valid and not expired/used, mark used and return user_id; else None."""


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

    async def count_by_subjects_and_document_type(
        self,
        tenant_id: str,
        subject_ids: list[str],
        document_type: str,
    ) -> int:
        """Count non-deleted documents for the given subjects and document_type."""

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


# Flow repository interface
class IFlowRepository(Protocol):
    """Protocol for flow repository (workflow instance grouping)."""

    async def get_by_id(self, flow_id: str, tenant_id: str) -> "FlowResult | None":
        """Return flow by ID if it belongs to tenant."""

    async def get_entity_by_id_and_tenant(
        self, flow_id: str, tenant_id: str
    ) -> object | None:
        """Return Flow ORM entity for write operations (update, delete)."""

    async def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        workflow_id: str | None = None,
    ) -> list[FlowResult]:
        """Return flows for tenant with optional workflow filter."""

    async def create_flow(
        self,
        tenant_id: str,
        name: str,
        *,
        workflow_id: str | None = None,
        hierarchy_values: dict[str, str] | None = None,
        subject_ids: list[str] | None = None,
        subject_roles: dict[str, str] | None = None,
    ) -> FlowResult:
        """Create a flow and optionally link subjects (role by subject_id)."""

    async def update_flow(
        self,
        flow_id: str,
        tenant_id: str,
        *,
        name: str | None = None,
        hierarchy_values: dict[str, str] | None = None,
    ) -> "FlowResult | None":
        """Update flow name or hierarchy_values; return updated result or None."""

    async def list_subjects_for_flow(
        self, flow_id: str, tenant_id: str
    ) -> list[FlowSubjectResult]:
        """Return flow-subject links for the flow (tenant-checked)."""

    async def add_subjects_to_flow(
        self,
        flow_id: str,
        tenant_id: str,
        subject_ids: list[str],
        roles: dict[str, str] | None = None,
    ) -> None:
        """Link subjects to flow (roles optional: subject_id -> role)."""

    async def remove_subject_from_flow(
        self, flow_id: str, subject_id: str, tenant_id: str
    ) -> bool:
        """Remove subject from flow; return True if removed."""


# Naming template repository interface
class INamingTemplateRepository(Protocol):
    """Protocol for naming template repository (flow/subject/document naming conventions)."""

    async def get_by_id(
        self, template_id: str, tenant_id: str
    ) -> "NamingTemplateResult | None":
        """Return naming template by ID if it belongs to tenant."""

    async def get_for_scope(
        self, tenant_id: str, scope_type: str, scope_id: str
    ) -> "NamingTemplateResult | None":
        """Return naming template for (tenant, scope_type, scope_id), or None."""

    async def get_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[NamingTemplateResult]:
        """Return naming templates for tenant with pagination."""

    async def create(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        template_string: str,
        placeholders: list[dict[str, Any]] | None = None,
    ) -> NamingTemplateResult:
        """Create a naming template; raise if duplicate (tenant, scope_type, scope_id)."""

    async def update(
        self,
        template_id: str,
        tenant_id: str,
        *,
        template_string: str | None = None,
        placeholders: list[dict[str, Any]] | None = None,
    ) -> "NamingTemplateResult | None":
        """Update template; return updated result or None if not found."""

    async def delete(self, template_id: str, tenant_id: str) -> bool:
        """Delete naming template; return True if deleted."""


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
    ) -> TaskResult:
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
    ) -> list[SearchResultItem]:
        """Search within tenant. scope: all | subjects | events | documents. Returns ranked results."""


# Audit log repository interface (append-only)
class IAuditLogRepository(Protocol):
    """Protocol for API audit log repository (DIP). Append-only."""

    async def create(self, entry: AuditLogEntryCreate) -> AuditLogResult:
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
    ) -> list[AuditLogResult]:
        """List audit log entries for tenant with optional filters (paginated)."""

    async def count(
        self,
        tenant_id: str,
        *,
        resource_type: str | None = None,
        user_id: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
    ) -> int:
        """Return total count of audit log entries for tenant with optional filters."""
