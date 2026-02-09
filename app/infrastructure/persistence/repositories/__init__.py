"""Persistence repositories. Re-exports for dependency injection."""

from app.infrastructure.persistence.repositories.auditable_repo import AuditableRepository
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.infrastructure.persistence.repositories.document_repo import DocumentRepository
from app.infrastructure.persistence.repositories.event_repo import EventRepository
from app.infrastructure.persistence.repositories.event_schema_repo import (
    EventSchemaRepository,
)
from app.infrastructure.persistence.repositories.oauth_provider_config_repo import (
    OAuthProviderConfigRepository,
)
from app.infrastructure.persistence.repositories.permission_repo import (
    PermissionRepository,
)
from app.infrastructure.persistence.repositories.role_repo import RoleRepository
from app.infrastructure.persistence.repositories.subject_repo import SubjectRepository
from app.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.user_repo import UserRepository
from app.infrastructure.persistence.repositories.workflow_repo import WorkflowRepository

__all__ = [
    "AuditableRepository",
    "BaseRepository",
    "DocumentRepository",
    "EventRepository",
    "EventSchemaRepository",
    "OAuthProviderConfigRepository",
    "PermissionRepository",
    "RoleRepository",
    "SubjectRepository",
    "TenantRepository",
    "UserRepository",
    "WorkflowRepository",
]
