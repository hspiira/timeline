"""Validates subject attributes (and optional display_name) against tenant subject type schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import jsonschema

from app.domain.exceptions import SchemaValidationException

if TYPE_CHECKING:
    from app.application.interfaces.repositories import ISubjectTypeRepository


class SubjectTypeSchemaValidator:
    """Validates subject attributes against subject type schema when type is configured with a schema."""

    def __init__(self, subject_type_repo: "ISubjectTypeRepository") -> None:
        self._repo = subject_type_repo

    async def validate_attributes(
        self,
        tenant_id: str,
        subject_type: str,
        attributes: dict[str, Any],
        display_name: str | None = None,
    ) -> None:
        """Validate attributes (and optionally display_name) against subject type schema.

        If no subject type config exists for tenant+type_name, or config has no schema, does nothing.
        Raises SchemaValidationException if schema exists and validation fails.
        """
        config = await self._repo.get_by_tenant_and_type(tenant_id, subject_type)
        if not config or not config.schema:
            return
        schema = config.schema
        # Validate attributes as the main payload
        try:
            jsonschema.validate(instance=attributes or {}, schema=schema)
        except jsonschema.ValidationError as e:
            raise SchemaValidationException(
                schema_type=f"subject_type:{subject_type}",
                validation_errors=[str(e)],
            ) from e
        except jsonschema.SchemaError as e:
            raise SchemaValidationException(
                schema_type=f"subject_type:{subject_type}",
                validation_errors=[str(e)],
            ) from e
