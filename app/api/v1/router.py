"""API v1 router aggregation.

Includes all endpoint modules with consistent prefix and tags. All routes
use dependencies from app.api.v1.dependencies (no manual repo/service construction).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    audit_log as audit_log_endpoint,
    auth,
    document_categories,
    documents,
    email_accounts,
    event_schemas,
    event_transition_rules,
    events,
    flows,
    health,
    naming_templates,
    oauth_providers,
    permissions,
    relationship_kinds,
    retention,
    roles,
    search,
    subject_types,
    subjects,
    tenants,
    user_roles,
    users,
)
from app.api.v1.endpoints import websocket as ws_endpoint
from app.api.v1.endpoints import workflows

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    analytics.router, prefix="/analytics", tags=["analytics"]
)
api_router.include_router(
    audit_log_endpoint.router, prefix="/audit-log", tags=["audit-log"]
)
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(
    document_categories.router,
    prefix="/document-categories",
    tags=["document-categories"],
)
api_router.include_router(
    email_accounts.router, prefix="/email-accounts", tags=["email-accounts"]
)
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(
    subject_types.router, prefix="/subject-types", tags=["subject-types"]
)
api_router.include_router(
    relationship_kinds.router,
    prefix="/relationship-kinds",
    tags=["relationship-kinds"],
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(user_roles.router, prefix="/users", tags=["user-roles"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(
    retention.router, prefix="/retention", tags=["retention"]
)
api_router.include_router(
    permissions.router, prefix="/permissions", tags=["permissions"]
)
api_router.include_router(
    event_schemas.router, prefix="/event-schemas", tags=["event-schemas"]
)
api_router.include_router(
    event_transition_rules.router,
    prefix="/event-transition-rules",
    tags=["event-transition-rules"],
)
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(flows.router, prefix="/flows", tags=["flows"])
api_router.include_router(
    naming_templates.router,
    prefix="/naming-templates",
    tags=["naming-templates"],
)
api_router.include_router(
    oauth_providers.router, prefix="/oauth-providers", tags=["oauth-providers"]
)
api_router.include_router(ws_endpoint.router, prefix="/ws", tags=["websocket"])
