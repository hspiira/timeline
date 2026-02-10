from fastapi import APIRouter

from app.api.v1.endpoints import (
    documents,
    event_schemas,
    events,
    health,
    subjects,
    tenants,
    users,
    workflows,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(event_schemas.router, prefix="/event-schemas", tags=["event-schemas"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
