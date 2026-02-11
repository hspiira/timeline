"""DTOs for user use cases (no dependency on ORM)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserResult:
    """User read-model (result of get_by_id, create_user, etc.). No password."""

    id: str
    tenant_id: str
    username: str
    email: str
    is_active: bool
