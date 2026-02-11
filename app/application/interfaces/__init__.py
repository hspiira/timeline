"""Application interfaces (ports): repository and service protocols.

Define contracts for infrastructure implementations (DIP).
No runtime imports from app.infrastructure or app.presentation.
"""

from app.application.interfaces.repositories import (
    IDocumentRepository,
    IEventRepository,
    IEventSchemaRepository,
    IPermissionRepository,
    IRolePermissionRepository,
    IRoleRepository,
    ISubjectRepository,
    ITenantRepository,
    IUserRepository,
)
from app.application.interfaces.services import (
    IAuditService,
    ICacheService,
    IEventService,
    IHashService,
    IPermissionResolver,
    ITenantInitializationService,
    IWorkflowEngine,
)
from app.application.interfaces.storage import IStorageService

__all__ = [
    "IAuditService",
    "ICacheService",
    "IDocumentRepository",
    "IEventRepository",
    "IEventSchemaRepository",
    "IEventService",
    "IHashService",
    "IPermissionRepository",
    "IPermissionResolver",
    "IRolePermissionRepository",
    "IRoleRepository",
    "IStorageService",
    "ISubjectRepository",
    "ITenantInitializationService",
    "ITenantRepository",
    "IUserRepository",
    "IWorkflowEngine",
]
