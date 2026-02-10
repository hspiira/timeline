"""Application interfaces (ports): repository and service protocols.

Define contracts for infrastructure implementations (DIP).
No runtime imports from app.infrastructure or app.presentation.
"""

from app.application.interfaces.repositories import (
    IDocumentRepository,
    IEventRepository,
    IEventSchemaRepository,
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
    "IPermissionResolver",
    "IStorageService",
    "ISubjectRepository",
    "ITenantInitializationService",
    "ITenantRepository",
    "IUserRepository",
    "IWorkflowEngine",
]
