"""Pydantic request/response schemas for the API."""

from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.email_account import EmailAccountResponse
from app.schemas.health import HealthResponse
from app.schemas.event import EventCreate, EventListResponse, EventResponse
from app.schemas.oauth_provider_config import OAuthConfigResponse
from app.schemas.permission import PermissionResponse
from app.schemas.role import RoleResponse
from app.schemas.event_schema import (
    EventSchemaCreateRequest,
    EventSchemaListItem,
    EventSchemaResponse,
)
from app.schemas.subject import SubjectCreateRequest, SubjectResponse
from app.schemas.tenant import TenantCreateRequest, TenantCreateResponse
from app.schemas.user import UserCreateRequest, UserResponse
from app.schemas.websocket import WebSocketStatusResponse
from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse

__all__ = [
    "EmailAccountResponse",
    "HealthResponse",
    "OAuthConfigResponse",
    "PermissionResponse",
    "RoleResponse",
    "LoginRequest",
    "TokenResponse",
    "EventCreate",
    "EventListResponse",
    "EventResponse",
    "EventSchemaCreateRequest",
    "EventSchemaListItem",
    "EventSchemaResponse",
    "SubjectCreateRequest",
    "SubjectResponse",
    "TenantCreateRequest",
    "TenantCreateResponse",
    "UserCreateRequest",
    "UserResponse",
    "WebSocketStatusResponse",
    "WorkflowCreateRequest",
    "WorkflowResponse",
]
