"""Application interfaces (ports): repository and service protocols.

Define contracts for infrastructure implementations (DIP).
No runtime imports from app.infrastructure or app.presentation.
"""

from app.application.interfaces.repositories import (
    IDocumentCategoryRepository,
    IDocumentRepository,
    IEventRepository,
    IEventSchemaRepository,
    IPermissionRepository,
    IRelationshipKindRepository,
    IRolePermissionRepository,
    IRoleRepository,
    ISearchRepository,
    ISubjectRelationshipRepository,
    ISubjectRepository,
    ISubjectTypeRepository,
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
    "IDocumentCategoryRepository",
    "IDocumentRepository",
    "IEventRepository",
    "IEventSchemaRepository",
    "IEventService",
    "IHashService",
    "IPermissionRepository",
    "IPermissionResolver",
    "IRelationshipKindRepository",
    "IRolePermissionRepository",
    "IRoleRepository",
    "ISearchRepository",
    "ISubjectRelationshipRepository",
    "ISubjectRepository",
    "ISubjectTypeRepository",
    "ITenantInitializationService",
    "ITenantRepository",
    "IUserRepository",
    "IWorkflowEngine",
]
