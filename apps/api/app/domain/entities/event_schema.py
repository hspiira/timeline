"""EventSchema domain entity.

Represents the validation contract for event payloads with immutable versioning.
Schema content and version are immutable; active flag is set at construction or via copy.
"""

from dataclasses import dataclass, replace
from typing import Any

from app.domain.exceptions import ValidationException
from app.domain.value_objects.core import EventType


@dataclass(frozen=True)
class EventSchemaEntity:
    """Immutable domain entity for event schema (SRP).

    Schemas define the structure of event payloads per event_type. Version and
    definition are immutable; use activated()/deactivated() for a new instance
    with a different is_active (persist via application/repo layer).
    """

    id: str
    tenant_id: str
    event_type: EventType
    schema_definition: dict[str, Any]
    version: int
    is_active: bool
    created_by: str | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate schema business rules. Raises ValidationException if invalid."""
        if not self.id:
            raise ValidationException("Schema ID is required", field="id")
        if not self.tenant_id:
            raise ValidationException("Schema must belong to a tenant", field="tenant_id")
        if not self.event_type:
            raise ValidationException("Schema must have an event type", field="event_type")
        if self.version < 1:
            raise ValidationException("Schema version must be positive", field="version")
        if not self.schema_definition:
            raise ValidationException("Schema definition cannot be empty", field="schema_definition")

    def can_validate_events(self) -> bool:
        """Return whether this schema can be used for new event validation."""
        return self.is_active

    def is_compatible_with(self, previous: "EventSchemaEntity") -> bool:
        """Check if this schema is backward-compatible with a previous version."""
        if previous.event_type.value != self.event_type.value:
            raise ValueError("Cannot compare schemas for different event types")
        prev_required = set(previous.schema_definition.get("required", []))
        curr_required = set(self.schema_definition.get("required", []))
        return not (curr_required - prev_required)

    def activated(self) -> "EventSchemaEntity":
        """Return a new instance with is_active=True. Persist via repo."""
        if self.is_active:
            raise ValueError("Schema is already active")
        return replace(self, is_active=True)

    def deactivated(self) -> "EventSchemaEntity":
        """Return a new instance with is_active=False. Persist via repo."""
        if not self.is_active:
            raise ValueError("Schema is already inactive")
        return replace(self, is_active=False)
