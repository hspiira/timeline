"""Persistence models: ORM entities and mixins."""

from app.infrastructure.persistence.models.audit_log import AuditLog
from app.infrastructure.persistence.models.document import Document
from app.infrastructure.persistence.models.email_account import EmailAccount
from app.infrastructure.persistence.models.event import Event
from app.infrastructure.persistence.models.event_schema import EventSchema
from app.infrastructure.persistence.models.mixins import (
    AuditedMultiTenantModel,
    CuidMixin,
    FullAuditMixin,
    FullyAuditedMultiTenantModel,
    MultiTenantModel,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UserAuditMixin,
    VersionedMixin,
)
from app.infrastructure.persistence.models.oauth_provider_config import (
    OAuthAuditLog,
    OAuthProviderConfig,
    OAuthState,
)
from app.infrastructure.persistence.models.permission import (
    Permission,
    RolePermission,
    UserRole,
)
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.models.subject import Subject
from app.infrastructure.persistence.models.subject_snapshot import SubjectSnapshot
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.models.workflow import Workflow, WorkflowExecution

__all__ = [
    "AuditLog",
    "Tenant",
    "User",
    "Subject",
    "SubjectSnapshot",
    "Task",
    "Event",
    "Document",
    "EventSchema",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "Workflow",
    "WorkflowExecution",
    "EmailAccount",
    "OAuthProviderConfig",
    "OAuthState",
    "OAuthAuditLog",
    "CuidMixin",
    "TenantMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "UserAuditMixin",
    "VersionedMixin",
    "FullAuditMixin",
    "MultiTenantModel",
    "AuditedMultiTenantModel",
    "FullyAuditedMultiTenantModel",
]
