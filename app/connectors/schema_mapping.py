"""Schema mapping: source columns and rules to event type (CDC/Kafka → EventCreate)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnMapping:
    """Maps a source column to a target field on the event.

    target_field values:
        "subject_id"       — maps to subject_id
        "event_time"      — maps to event_time
        "payload.STATUS"  — maps to payload["STATUS"]
        "correlation_id"   — maps to correlation_id
    """

    source_column: str
    target_field: str


@dataclass
class EventTypeRule:
    """Rule to resolve event_type from a source row and operation."""

    event_type: str
    condition: str | None = None
    priority: int = 0

    # condition is a Python expression evaluated with row data in scope.
    # None means "default" — matches if no prior rule matched.


@dataclass
class TableMapping:
    """Mapping from a source table to subject_type, columns, and event_type rules."""

    source_table: str
    subject_type: str
    column_mappings: list[ColumnMapping]
    event_type_rules: list[EventTypeRule]
    default_schema_version: int = 1

    def resolve_event_type(
        self, row: dict[str, Any], operation: str
    ) -> str | None:
        """Evaluate rules in priority order; return first match."""
        context = {"row": row, "operation": operation, **row}
        for rule in sorted(self.event_type_rules, key=lambda r: -r.priority):
            if rule.condition is None:
                return rule.event_type
            try:
                if eval(rule.condition, {"__builtins__": {}}, context):
                    return rule.event_type
            except Exception:
                continue
        return None
