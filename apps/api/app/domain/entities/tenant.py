"""Tenant domain entity.

Represents the business concept of a tenant, independent of persistence.
"""

from dataclasses import dataclass

from app.domain.enums import TenantStatus
from app.domain.exceptions import ValidationException
from app.domain.value_objects.core import TenantCode


@dataclass
class TenantEntity:
    """Domain entity for tenant (SRP: business logic separate from persistence).

    Encapsulates tenant lifecycle (active/suspended/archived) and
    business rules. Validation runs on construction.
    """

    id: str
    code: TenantCode
    name: str
    status: TenantStatus

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate tenant business rules. Raises ValidationException if invalid."""
        if not self.id:
            raise ValidationException("Tenant ID is required", field="id")
        if not self.name or not self.name.strip():
            raise ValidationException("Tenant name is required", field="name")

    def can_create_events(self) -> bool:
        """Return whether this tenant is allowed to create events.

        Returns:
            True only when status is ACTIVE.
        """
        return self.status == TenantStatus.ACTIVE

    def activate(self) -> None:
        """Set tenant to ACTIVE. Idempotent when already ACTIVE.

        Suspended tenants can be activated. No-op if status is already ACTIVE.

        Raises:
            ValueError: If tenant is ARCHIVED.
        """
        if self.status == TenantStatus.ARCHIVED:
            raise ValueError("Tenant is archived")
        self.status = TenantStatus.ACTIVE

    def suspend(self) -> None:
        """Set tenant to SUSPENDED. Idempotent when already SUSPENDED.

        Active tenants can be suspended. No-op if status is already SUSPENDED.

        Raises:
            ValueError: If tenant is ARCHIVED.
        """
        if self.status == TenantStatus.ARCHIVED:
            raise ValueError("Tenant is archived")
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
        """Change tenant code. Not allowed when ACTIVE or ARCHIVED.

        Args:
            new_code: New tenant code value object.

        Raises:
            ValueError: If tenant is ACTIVE or ARCHIVED (code is immutable).
        """
        if self.status == TenantStatus.ACTIVE:
            raise ValueError("Tenant is active")
        if self.status == TenantStatus.ARCHIVED:
            raise ValueError("Tenant is archived")
        self.code = new_code
