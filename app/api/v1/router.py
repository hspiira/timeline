"""API v1 router aggregation.

Includes all endpoint modules with consistent prefix and tags. All routes
use dependencies from app.api.v1.dependencies (no manual repo/service construction).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    documents,
    email_accounts,
    event_schemas,
    events,
    health,
    oauth_providers,
    permissions,
    roles,
    subjects,
    tenants,
    user_roles,
    users,
    websocket as ws_endpoint,
    workflows,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(
    email_accounts.router, prefix="/email-accounts", tags=["email-accounts"]
)
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    user_roles.router, prefix="/users", tags=["user-roles"]
)
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(
    event_schemas.router, prefix="/event-schemas", tags=["event-schemas"]
)
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(
    oauth_providers.router, prefix="/oauth-providers", tags=["oauth-providers"]
)
api_router.include_router(ws_endpoint.router, tags=["websocket"])
