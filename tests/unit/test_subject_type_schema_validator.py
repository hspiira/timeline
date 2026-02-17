"""Tests for SubjectTypeSchemaValidator (mocked subject type repo)."""

from typing import Any

import pytest

from app.application.dtos.subject_type import SubjectTypeResult
from app.application.services.subject_type_schema_validator import (
    SubjectTypeSchemaValidator,
)
from app.domain.exceptions import SchemaValidationException


def _config(
    type_name: str = "client",
    schema: dict[str, Any] | None = None,
) -> SubjectTypeResult:
    return SubjectTypeResult(
        id="st1",
        tenant_id="t1",
        type_name=type_name,
        display_name="Client",
        description=None,
        schema=schema or {"type": "object", "properties": {"name": {"type": "string"}}},
        version=1,
        is_active=True,
        icon=None,
        color=None,
        has_timeline=True,
        allow_documents=True,
        created_by=None,
    )


@pytest.fixture
def validator_with_mocks():
    """SubjectTypeSchemaValidator with async mock repo."""

    class MockSubjectTypeRepo:
        def __init__(self, config: SubjectTypeResult | None = None):
            self.config = config

        async def get_by_tenant_and_type(
            self, tenant_id: str, type_name: str
        ) -> SubjectTypeResult | None:
            return self.config

    def make_validator(
        config: SubjectTypeResult | None = None,
    ) -> SubjectTypeSchemaValidator:
        return SubjectTypeSchemaValidator(subject_type_repo=MockSubjectTypeRepo(config))

    return make_validator


async def test_no_config_does_nothing(validator_with_mocks) -> None:
    """When no config exists for tenant+type, validate_attributes returns without raising."""
    v = validator_with_mocks(config=None)
    await v.validate_attributes("t1", "client", {})
    await v.validate_attributes("t1", "client", {"name": "x"})


async def test_config_without_schema_does_nothing(validator_with_mocks) -> None:
    """When config has no schema, validate_attributes returns without raising."""
    v = validator_with_mocks(config=_config(schema=None))
    await v.validate_attributes("t1", "client", {"anything": 1})


async def test_valid_attributes_passes(validator_with_mocks) -> None:
    """When attributes conform to schema, no exception."""
    v = validator_with_mocks(config=_config())
    await v.validate_attributes("t1", "client", {"name": "Acme"})


async def test_invalid_attributes_raises(validator_with_mocks) -> None:
    """When attributes fail jsonschema validation, SchemaValidationException is raised."""
    v = validator_with_mocks(config=_config())
    with pytest.raises(SchemaValidationException) as exc_info:
        await v.validate_attributes("t1", "client", {"name": 123})
    assert exc_info.value.error_code == "SCHEMA_VALIDATION_ERROR"
    assert "subject_type:client" in exc_info.value.message


async def test_empty_attributes_valid_against_schema(validator_with_mocks) -> None:
    """Attributes can be empty dict when schema allows it."""
    v = validator_with_mocks(
        config=_config(schema={"type": "object", "properties": {}})
    )
    await v.validate_attributes("t1", "client", {})
