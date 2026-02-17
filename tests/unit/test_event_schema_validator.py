"""Tests for EventSchemaValidator (mocked schema repo)."""

from typing import Any

import pytest

from app.application.dtos.event_schema import EventSchemaResult
from app.application.services.event_schema_validator import EventSchemaValidator
from app.domain.exceptions import ResourceNotFoundException, SchemaValidationException
from app.domain.value_objects.core import EventType


def _schema(
    event_type: str = "status_changed",
    version: int = 1,
    is_active: bool = True,
    schema_definition: dict[str, Any] | None = None,
) -> EventSchemaResult:
    return EventSchemaResult(
        id="s1",
        tenant_id="t1",
        event_type=EventType(event_type),
        schema_definition=schema_definition or {"type": "object", "properties": {"status": {"type": "string"}}},
        version=version,
        is_active=is_active,
        created_by=None,
    )


@pytest.fixture
def validator_with_mocks():
    """EventSchemaValidator with async mock schema_repo."""

    class MockSchemaRepo:
        def __init__(self, schema: EventSchemaResult | None = None):
            self.schema = schema

        async def get_by_version(
            self, tenant_id: str, event_type: str, version: int
        ) -> EventSchemaResult | None:
            return self.schema

    def make_validator(schema: EventSchemaResult | None = None) -> EventSchemaValidator:
        return EventSchemaValidator(schema_repo=MockSchemaRepo(schema))

    return make_validator


async def test_schema_not_found_raises(validator_with_mocks) -> None:
    """When get_by_version returns None, ResourceNotFoundException is raised."""
    v = validator_with_mocks(schema=None)
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await v.validate_payload("t1", "status_changed", 1, {"status": "ok"})
    assert exc_info.value.details["resource_type"] == "event_schema"
    assert "status_changed@v1" in exc_info.value.details["resource_id"]


async def test_inactive_schema_raises(validator_with_mocks) -> None:
    """When schema exists but is_active is False, SchemaValidationException is raised."""
    v = validator_with_mocks(schema=_schema(is_active=False))
    with pytest.raises(SchemaValidationException) as exc_info:
        await v.validate_payload("t1", "status_changed", 1, {"status": "ok"})
    assert "not active" in str(exc_info.value.details.get("errors", []))


async def test_valid_payload_passes(validator_with_mocks) -> None:
    """When payload conforms to schema_definition, no exception."""
    v = validator_with_mocks(schema=_schema())
    await v.validate_payload("t1", "status_changed", 1, {"status": "draft"})


async def test_invalid_payload_raises(validator_with_mocks) -> None:
    """When payload fails jsonschema validation, SchemaValidationException is raised."""
    # schema requires "status" string; we pass wrong type
    v = validator_with_mocks(schema=_schema())
    with pytest.raises(SchemaValidationException) as exc_info:
        await v.validate_payload("t1", "status_changed", 1, {"status": 123})
    assert exc_info.value.error_code == "SCHEMA_VALIDATION_ERROR"
    assert "status_changed@v1" in exc_info.value.message
