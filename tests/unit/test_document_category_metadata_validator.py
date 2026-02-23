"""Tests for DocumentCategoryMetadataValidator (mocked document category repo)."""

from typing import Any

import pytest

from app.application.dtos.document_category import DocumentCategoryResult
from app.application.services.document_category_metadata_validator import (
    DocumentCategoryMetadataValidator,
)
from app.domain.exceptions import SchemaValidationException


def _category(
    category_name: str = "invoice",
    metadata_schema: dict[str, Any] | None = None,
) -> DocumentCategoryResult:
    return DocumentCategoryResult(
        id="cat1",
        tenant_id="t1",
        category_name=category_name,
        display_name="Invoice",
        description=None,
        metadata_schema=metadata_schema
        or {"type": "object", "properties": {"invoice_number": {"type": "string"}}},
        default_retention_days=None,
        is_active=True,
        created_by=None,
    )


@pytest.fixture
def validator_with_mocks():
    """DocumentCategoryMetadataValidator with async mock repo."""

    class MockDocumentCategoryRepo:
        def __init__(self, category: DocumentCategoryResult | None = None):
            self.category = category

        async def get_by_tenant_and_name(
            self, tenant_id: str, category_name: str
        ) -> DocumentCategoryResult | None:
            return self.category

    def make_validator(
        category: DocumentCategoryResult | None = None,
    ) -> DocumentCategoryMetadataValidator:
        return DocumentCategoryMetadataValidator(
            category_repo=MockDocumentCategoryRepo(category)
        )

    return make_validator


async def test_no_category_does_nothing(validator_with_mocks) -> None:
    """When no category exists for tenant+document_type, validate_metadata returns without raising."""
    v = validator_with_mocks(category=None)
    await v.validate_metadata("t1", "invoice", {})
    await v.validate_metadata("t1", "invoice", {"invoice_number": "INV-1"})


async def test_category_without_metadata_schema_does_nothing(
    validator_with_mocks,
) -> None:
    """When category has no metadata_schema, validate_metadata returns without raising."""
    v = validator_with_mocks(category=_category(metadata_schema=None))
    await v.validate_metadata("t1", "invoice", {"anything": 1})


async def test_valid_metadata_passes(validator_with_mocks) -> None:
    """When metadata conforms to metadata_schema, no exception."""
    v = validator_with_mocks(category=_category())
    await v.validate_metadata("t1", "invoice", {"invoice_number": "INV-001"})


async def test_invalid_metadata_raises(validator_with_mocks) -> None:
    """When metadata fails jsonschema validation, SchemaValidationException is raised."""
    v = validator_with_mocks(category=_category())
    with pytest.raises(SchemaValidationException) as exc_info:
        await v.validate_metadata("t1", "invoice", {"invoice_number": 12345})
    assert exc_info.value.error_code == "SCHEMA_VALIDATION_ERROR"
    assert "document_category:invoice" in exc_info.value.message


async def test_empty_metadata_valid_against_schema(validator_with_mocks) -> None:
    """Metadata can be empty dict when schema allows it."""
    v = validator_with_mocks(
        category=_category(
            metadata_schema={"type": "object", "properties": {}}
        )
    )
    await v.validate_metadata("t1", "invoice", {})
