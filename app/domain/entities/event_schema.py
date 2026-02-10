"""EventSchema domain entity.

Represents the validation contract for event payloads with immutable versioning.
"""

from dataclasses import dataclass
from typing import Any

from app.domain.value_objects.core import EventType


@dataclass
class EventSchemaEntity:
    """Domain entity for event schema (SRP).

    Schemas define the structure of event payloads per event_type.
    Immutable versioning: schemas are not modified, only new versions created.
    """

    id: str
    tenant_id: str
    event_type: EventType
    schema_definition: dict[str, Any]
    version: int
    is_active: bool
    created_by: str | None = None

    def validate(self) -> bool:
        """Validate schema business rules.

        Returns:
            True if valid.

        Raises:
            ValueError: If version < 1 or schema_definition is empty.
        """
        if self.version < 1:
            raise ValueError("Schema version must be positive")
        if not self.schema_definition:
            raise ValueError("Schema definition cannot be empty")
        return True

    def can_validate_events(self) -> bool:
        """Return whether this schema can be used for new event validation.

        Returns:
            True only when schema is active.
        """
        return self.is_active

    def is_compatible_with(self, previous: "EventSchemaEntity") -> bool:
        """Check if this schema is backward-compatible with a previous version.

        New required properties in current schema break compatibility.
        Real implementation could use JSON Schema compatibility analysis.

        Args:
            previous: The previous schema version to compare against.

        Returns:
            True if current schema is backward-compatible.

        Raises:
            ValueError: If schemas are for different event types.
        """
        if previous.event_type.value != self.event_type.value:
            raise ValueError("Cannot compare schemas for different event types")
        prev_required = set(previous.schema_definition.get("required", []))
        curr_required = set(self.schema_definition.get("required", []))
        return not (curr_required - prev_required)

    def activate(self) -> None:
        """Mark this schema version as active.

        Only one version per event_type should be active; deactivation of
        others is handled in the use case / application layer.

        Raises:
            ValueError: If already active.
        """
        if self.is_active:
            raise ValueError("Schema is already active")
        self.is_active = True

    def deactivate(self) -> None:
        """Mark this schema version as inactive.

        Raises:
            ValueError: If already inactive.
        """
        if not self.is_active:
            raise ValueError("Schema is already inactive")
        self.is_active = False
