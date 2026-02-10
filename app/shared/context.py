"""Request context management using contextvars.

Provides thread-safe, async-safe storage for request-scoped data such as
the current user. Similar to Flask's `g` or Django's request.user.

Usage:
    set_current_user(user_id="user123", actor_type=ActorType.USER)
    user_id = get_current_actor_id()
    actor_type = get_current_actor_type()
"""

from contextvars import ContextVar
from dataclasses import dataclass

from app.shared.enums import ActorType

_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
_current_actor_type: ContextVar[ActorType] = ContextVar(
    "current_actor_type", default=ActorType.SYSTEM
)
_current_ip_address: ContextVar[str | None] = ContextVar(
    "current_ip_address", default=None
)
_current_user_agent: ContextVar[str | None] = ContextVar(
    "current_user_agent", default=None
)


@dataclass(frozen=True)
class ActorContext:
    """Immutable snapshot of the current actor context."""

    user_id: str | None
    actor_type: ActorType
    ip_address: str | None = None
    user_agent: str | None = None


def set_current_user(
    user_id: str | None,
    actor_type: ActorType = ActorType.USER,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Set the current user context for this request.

    Call in middleware or dependency injection after authentication.
    Context is scoped to the current async task/thread.

    Args:
        user_id: Authenticated user ID or None.
        actor_type: Who is performing the action (USER, SYSTEM, EXTERNAL).
        ip_address: Optional client IP.
        user_agent: Optional client user agent.

    Raises:
        ValueError: If actor_type is USER and user_id is None or empty.
    """
    if actor_type == ActorType.USER and not user_id:
        raise ValueError("user_id is required when actor_type is USER")
    _current_user_id.set(user_id)
    _current_actor_type.set(actor_type)
    _current_ip_address.set(ip_address)
    _current_user_agent.set(user_agent)


def clear_current_user() -> None:
    """Clear the current user context."""
    _current_user_id.set(None)
    _current_actor_type.set(ActorType.SYSTEM)
    _current_ip_address.set(None)
    _current_user_agent.set(None)


def get_current_actor_id() -> str | None:
    """Return the current user ID, or None if not authenticated."""
    return _current_user_id.get()


def get_current_actor_type() -> ActorType:
    """Return the current actor type (defaults to SYSTEM if not set)."""
    return _current_actor_type.get()


def get_current_ip_address() -> str | None:
    """Return the current request IP address."""
    return _current_ip_address.get()


def get_current_user_agent() -> str | None:
    """Return the current request user agent."""
    return _current_user_agent.get()


def get_actor_context() -> ActorContext:
    """Return a snapshot of the current actor context."""
    return ActorContext(
        user_id=_current_user_id.get(),
        actor_type=_current_actor_type.get(),
        ip_address=_current_ip_address.get(),
        user_agent=_current_user_agent.get(),
    )
