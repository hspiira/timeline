"""System audit schema definition (JSON Schema and constants).

Used by tenant initialization and audit service. No infrastructure deps.
"""

from typing import Any

SYSTEM_AUDIT_EVENT_TYPE = "system.audit"
SYSTEM_AUDIT_SUBJECT_TYPE = "system_audit"
SYSTEM_AUDIT_SUBJECT_REF = "_system_audit_trail"
SYSTEM_AUDIT_SCHEMA_VERSION = 1

AUDITABLE_ENTITIES = frozenset({
    "subject", "event_schema", "workflow", "user", "role", "permission",
    "document", "tenant", "email_account", "oauth_provider",
})
AUDIT_ACTIONS = frozenset({
    "created", "updated", "deleted", "activated", "deactivated",
    "assigned", "unassigned", "status_changed",
})
ACTOR_TYPES = frozenset({"user", "system", "external", "api_key", "webhook"})


def get_system_audit_schema_definition() -> dict[str, Any]:
    """Return JSON Schema for system audit events (strict validation)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "System Audit Event",
        "description": "Schema for tracking all system CRUD operations",
        "type": "object",
        "required": ["entity_type", "entity_id", "action", "actor", "timestamp"],
        "additionalProperties": False,
        "properties": {
            "entity_type": {
                "type": "string",
                "description": "Type of entity being audited",
                "enum": list(AUDITABLE_ENTITIES),
            },
            "entity_id": {
                "type": "string",
                "description": "CUID of the affected entity",
                "minLength": 1,
                "maxLength": 128,
            },
            "action": {
                "type": "string",
                "description": "The action performed on the entity",
                "enum": list(AUDIT_ACTIONS),
            },
            "actor": {
                "type": "object",
                "description": "Who or what performed the action",
                "required": ["type"],
                "additionalProperties": False,
                "properties": {
                    "type": {"type": "string", "enum": list(ACTOR_TYPES)},
                    "id": {"type": ["string", "null"], "maxLength": 128},
                    "ip_address": {"type": ["string", "null"], "maxLength": 45},
                    "user_agent": {"type": ["string", "null"], "maxLength": 512},
                },
            },
            "timestamp": {
                "type": "string",
                "description": "ISO 8601 timestamp",
                "format": "date-time",
            },
            "entity_data": {
                "type": "object",
                "description": "Snapshot of the entity",
                "additionalProperties": True,
            },
            "changes": {"type": ["object", "null"]},
            "metadata": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "request_id": {"type": ["string", "null"]},
                    "reason": {"type": ["string", "null"]},
                    "source": {"type": ["string", "null"]},
                },
            },
        },
    }
