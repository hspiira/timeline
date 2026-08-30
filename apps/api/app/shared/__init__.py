"""Shared utilities: context, enums, telemetry, and cross-cutting helpers.

Used by domain, application, and infrastructure. No business logic.
"""

from app.shared.context import (
    ActorContext,
    clear_current_user,
    get_actor_context,
    get_current_actor_id,
    get_current_actor_type,
    get_current_ip_address,
    get_current_user_agent,
    set_current_user,
)
from app.shared.enums import (
    ActorType,
    AuditAction,
    DocumentAccessLevel,
    OAuthStatus,
    WorkflowExecutionStatus,
)
from app.shared.utils import (
    ensure_utc,
    from_timestamp_ms_utc,
    from_timestamp_utc,
    generate_cuid,
    utc_now,
)

__all__ = [
    "set_current_user",
    "clear_current_user",
    "get_current_actor_id",
    "get_current_actor_type",
    "get_current_ip_address",
    "get_current_user_agent",
    "get_actor_context",
    "ActorContext",
    "ActorType",
    "AuditAction",
    "DocumentAccessLevel",
    "OAuthStatus",
    "WorkflowExecutionStatus",
    "generate_cuid",
    "utc_now",
    "ensure_utc",
    "from_timestamp_utc",
    "from_timestamp_ms_utc",
]
