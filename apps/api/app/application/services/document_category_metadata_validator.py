"""Validates document metadata against tenant document category metadata_schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import jsonschema

from app.domain.exceptions import SchemaValidationException

if TYPE_CHECKING:
    from app.application.interfaces.repositories import IDocumentCategoryRepository


class DocumentCategoryMetadataValidator:
    """Validates document metadata against document category metadata_schema when category is configured."""

    def __init__(self, category_repo: "IDocumentCategoryRepository") -> None:
        self._repo = category_repo

    async def validate_metadata(
        self,
        tenant_id: str,
        document_type: str,
        metadata: dict[str, Any],
    ) -> None:
        """Validate metadata against category's metadata_schema.

        If no document category exists for tenant+document_type, or category has no
        metadata_schema, does nothing. Raises SchemaValidationException if schema
        exists and validation fails.
        """
        category = await self._repo.get_by_tenant_and_name(
            tenant_id, document_type
        )
        if not category or not category.metadata_schema:
            return
        schema = category.metadata_schema
        try:
            jsonschema.validate(instance=metadata or {}, schema=schema)
        except jsonschema.ValidationError as e:
            raise SchemaValidationException(
                schema_type=f"document_category:{document_type}",
                validation_errors=[str(e)],
            ) from e
        except jsonschema.SchemaError as e:
            raise SchemaValidationException(
                schema_type=f"document_category:{document_type}",
                validation_errors=[str(e)],
            ) from e
