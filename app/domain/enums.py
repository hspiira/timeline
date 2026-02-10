"""Domain enumerations for the Timeline application.

Enums represent fixed sets of domain values (e.g. tenant status).
"""

from enum import Enum


class TenantStatus(str, Enum):
    """Tenant lifecycle status.

    Determines whether a tenant can create events and accept API traffic.
    """

    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid status values as strings.

        Returns:
            List of enum value strings (e.g. for validation or serialization).
        """
        return [status.value for status in cls]
