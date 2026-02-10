"""Subject domain entity.

Represents the business concept of a subject, independent of persistence.
"""

from dataclasses import dataclass, field

from app.domain.value_objects.core import SubjectType


@dataclass
class SubjectEntity:
    """Domain entity for subject (SRP: business logic separate from persistence).

    A subject is the entity whose timeline (event chain) is being maintained.
    Optional internal state (_event_count, _has_events) supports chain queries.
    """

    id: str
    tenant_id: str
    subject_type: SubjectType
    external_ref: str | None

    _event_count: int = field(default=0, repr=False)
    _has_events: bool = field(default=False, repr=False)

    def validate(self) -> bool:
        """Validate subject business rules.

        Returns:
            True if valid.

        Raises:
            ValueError: If id or tenant_id is missing.
        """
        if not self.id:
            raise ValueError("Subject ID is required")
        if not self.tenant_id:
            raise ValueError("Subject must belong to a tenant")
        return True

    def belongs_to_tenant(self, tenant_id: str) -> bool:
        """Return whether this subject belongs to the given tenant.

        Args:
            tenant_id: Tenant ID to check.

        Returns:
            True if subject's tenant_id matches.
        """
        return self.tenant_id == tenant_id

    def can_receive_events(self) -> bool:
        """Return whether this subject can receive new events.

        Extension point for archived subjects, status lifecycle, or rate limiting.
        Currently always True.

        Returns:
            True if subject can receive events.
        """
        return True

    def is_genesis_subject(self) -> bool:
        """Return whether this subject has no events yet (empty timeline).

        Returns:
            True if no events have been added.
        """
        return not self._has_events

    def mark_has_events(self) -> None:
        """Record that an event has been added to this subject."""
        self._event_count += 1
        self._has_events = True
