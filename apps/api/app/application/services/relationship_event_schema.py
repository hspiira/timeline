"""Relationship event schema definition (JSON Schema) for relationship_added/relationship_removed.

Used by tenant initialization so relationship events are validated. No infrastructure deps.
"""

from typing import Any

RELATIONSHIP_ADDED_EVENT_TYPE = "relationship_added"
RELATIONSHIP_REMOVED_EVENT_TYPE = "relationship_removed"
RELATIONSHIP_EVENT_SCHEMA_VERSION = 1


def get_relationship_event_schema_definition() -> dict[str, Any]:
    """Return JSON Schema for relationship_added and relationship_removed event payloads.

    Payload must have related_subject_id (string) and relationship_kind (string).
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Relationship Event Payload",
        "description": "Payload for relationship_added and relationship_removed events",
        "type": "object",
        "required": ["related_subject_id", "relationship_kind"],
        "properties": {
            "related_subject_id": {"type": "string", "minLength": 1},
            "relationship_kind": {"type": "string", "minLength": 1, "maxLength": 100},
        },
        "additionalProperties": True,
    }
