"""Validates event payload against tenant event schema (implements IEventSchemaValidator)."""

from __future__ import annotations

from typing import Any

import jsonschema

from app.application.interfaces.repositories import IEventSchemaRepository
from app.application.interfaces.services import IEventSchemaValidator


class EventSchemaValidator:
    """Validates event payload against active schema; single responsibility."""

    def __init__(self, schema_repo: IEventSchemaRepository) -> None:
        self.schema_repo = schema_repo

    async def validate_payload(
        self,
        tenant_id: str,
        event_type: str,
        schema_version: int,
        payload: dict[str, Any],
    ) -> None:
        schema = await self.schema_repo.get_by_version(
            tenant_id, event_type, schema_version
        )
        if not schema:
            raise ValueError(
                f"Schema version {schema_version} not found for event type '{event_type}'"
            )
        if not schema.is_active:
            raise ValueError(
                f"Schema version {schema_version} for '{event_type}' is not active"
            )
        try:
            jsonschema.validate(instance=payload, schema=schema.schema_definition)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Payload validation failed against schema v{schema_version}: {e.message}"
            ) from e
        except jsonschema.SchemaError as e:
            raise ValueError(
                f"Invalid schema definition for v{schema_version}: {e.message}"
            ) from e
