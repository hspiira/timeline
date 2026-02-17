"""Persistence repositories. Re-exports for dependency injection."""

from app.infrastructure.persistence.repositories.audit_log_repo import (
    AuditLogRepository,
)
from app.infrastructure.persistence.repositories.auditable_repo import (
    AuditableRepository,
)
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.infrastructure.persistence.repositories.document_repo import DocumentRepository
from app.infrastructure.persistence.repositories.document_category_repo import (
    DocumentCategoryRepository,
)
from app.infrastructure.persistence.repositories.email_account_repo import (
    EmailAccountRepository,
)
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.event_schema_repo import (
    EventSchemaRepository,
)
from app.infrastructure.persistence.repositories.event_transition_rule_repo import (
    EventTransitionRuleRepository,
)
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)
from app.infrastructure.persistence.repositories.oauth_state_repo import (
    OAuthStateRepository,
)
from app.infrastructure.persistence.repositories.password_set_token_repo import (
    PasswordSetTokenStore,
)
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.infrastructure.persistence.repositories.role_permission_repo import (
    RolePermissionRepository,
)
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.infrastructure.persistence.repositories.search_repo import SearchRepository
from app.infrastructure.persistence.repositories.user_role_repo import (
    UserRoleRepository,
)
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.subject_snapshot_repo import (
    SubjectSnapshotRepository,
)
from app.infrastructure.persistence.repositories.subject_type_repo import (
    SubjectTypeRepository,
)
from app.infrastructure.persistence.repositories.task_repo import TaskRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.persistence.repositories.workflow_repo import (
    WorkflowExecutionRepository,
    WorkflowRepository,
)

__all__ = [
    "AuditLogRepository",
    "AuditableRepository",
    "BaseRepository",
    "DocumentCategoryRepository",
    "DocumentRepository",
    "EmailAccountRepository",
    "EventRepository",
    "EventSchemaRepository",
    "EventTransitionRuleRepository",
    "OAuthProviderConfigRepository",
    "OAuthStateRepository",
    "PasswordSetTokenStore",
    "PermissionRepository",
    "RolePermissionRepository",
    "RoleRepository",
    "SearchRepository",
    "UserRoleRepository",
    "SubjectRepository",
    "SubjectSnapshotRepository",
    "SubjectTypeRepository",
    "TaskRepository",
    "TenantRepository",
    "UserRepository",
    "WorkflowExecutionRepository",
    "WorkflowRepository",
]
