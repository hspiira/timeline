"""Tenant domain entity.

Represents the business concept of a tenant, independent of persistence.
"""

from dataclasses import dataclass

from app.domain.enums import TenantStatus
from app.domain.value_objects.core import TenantCode


@dataclass
class TenantEntity:
    """Domain entity for tenant (SRP: business logic separate from persistence).

    Encapsulates tenant lifecycle (active/suspended/archived) and
    business rules such as event creation and code immutability.
    """

    id: str
    code: TenantCode
    name: str
    status: TenantStatus

    def can_create_events(self) -> bool:
        """Return whether this tenant is allowed to create events.

        Returns:
            True only when status is ACTIVE.
        """
        return self.status == TenantStatus.ACTIVE

    def activate(self) -> None:
        """Set tenant to ACTIVE. Suspended tenants can be activated.

        Raises:
            ValueError: If tenant is ARCHIVED (archived cannot be activated).
        """
        if self.status == TenantStatus.ARCHIVED:
            raise ValueError("Archived tenants cannot be activated")
        self.status = TenantStatus.ACTIVE

    def suspend(self) -> None:
        """Set tenant to SUSPENDED. Active tenants can be suspended.

        Raises:
            ValueError: If tenant is ARCHIVED.
        """
        if self.status == TenantStatus.ARCHIVED:
            raise ValueError("Archived tenants cannot be suspended")
        self.status = TenantStatus.SUSPENDED

    def archive(self) -> None:
        """Set tenant to ARCHIVED. Archiving is irreversible.

        Raises:
            ValueError: If tenant is already archived.
        """
        if self.status == TenantStatus.ARCHIVED:
            raise ValueError("Tenant is already archived")
        self.status = TenantStatus.ARCHIVED

    def change_code(self, new_code: TenantCode) -> None:
        """Change tenant code. Not allowed once tenant is ACTIVE.

        Args:
            new_code: New tenant code value object.

        Raises:
            ValueError: If tenant is already active (code is immutable).
        """
        if self.status == TenantStatus.ACTIVE:
            raise ValueError("Tenant code cannot be changed once tenant is active")
        self.code = new_code
