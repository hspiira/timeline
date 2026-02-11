"""Validates event payload against tenant event schema (implements IEventSchemaValidator)."""

from __future__ import annotations

from typing import Any

import jsonschema

from app.application.interfaces.repositories import IEventSchemaRepository
from app.domain.exceptions import ResourceNotFoundException, SchemaValidationException


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
        schema_id = f"{event_type}@v{schema_version}"
        if not schema:
            raise ResourceNotFoundException("event_schema", schema_id)
        if not schema.is_active:
            raise SchemaValidationException(
                schema_type=schema_id,
                validation_errors=["Schema version is not active"],
            )
        try:
            jsonschema.validate(instance=payload, schema=schema.schema_definition)
        except jsonschema.ValidationError as e:
            raise SchemaValidationException(
                schema_type=schema_id,
                validation_errors=[str(e)],
            ) from e
        except jsonschema.SchemaError as e:
            raise SchemaValidationException(
                schema_type=schema_id,
                validation_errors=[str(e)],
            ) from e
