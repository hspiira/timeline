"""Unit tests for TenantInitializationService (GDPR wildcard exclusion, assign_admin_role)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.services.tenant_initialization_service import (
    DEFAULT_ROLES,
    GDPR_SENSITIVE_PERMISSIONS,
    TenantInitializationService,
)


def test_resolve_permission_pattern_subject_star_excludes_gdpr() -> None:
    """subject:* wildcard must not expand to subject:export or subject:erasure."""
    permission_map = {
        "subject:create": "pid-create",
        "subject:read": "pid-read",
        "subject:update": "pid-update",
        "subject:delete": "pid-delete",
        "subject:list": "pid-list",
        "subject:export": "pid-export",
        "subject:erasure": "pid-erasure",
    }
    result = TenantInitializationService._resolve_permission_pattern(
        "subject:*", permission_map
    )
    assert "pid-export" not in result
    assert "pid-erasure" not in result
    assert "pid-create" in result
    assert "pid-read" in result
    assert "pid-update" in result
    assert "pid-delete" in result
    assert "pid-list" in result
    assert len(result) == 5


def test_resolve_permission_pattern_exact_match_includes_gdpr() -> None:
    """Explicit subject:export or subject:erasure still resolve when given as exact pattern."""
    permission_map = {
        "subject:export": "pid-export",
        "subject:erasure": "pid-erasure",
    }
    assert TenantInitializationService._resolve_permission_pattern(
        "subject:export", permission_map
    ) == ["pid-export"]
    assert TenantInitializationService._resolve_permission_pattern(
        "subject:erasure", permission_map
    ) == ["pid-erasure"]


def test_manager_role_does_not_include_gdpr_permissions_in_default_config() -> None:
    """Manager uses subject:*; GDPR_SENSITIVE_PERMISSIONS should match what we exclude."""
    manager_permissions = DEFAULT_ROLES["manager"]["permissions"]
    assert "subject:*" in manager_permissions
    for gdpr in GDPR_SENSITIVE_PERMISSIONS:
        assert gdpr not in manager_permissions


@pytest.mark.asyncio
async def test_assign_admin_role_raises_resource_not_found_when_admin_role_missing() -> None:
    """assign_admin_role raises ResourceNotFoundException when admin role is not found."""
    tenant_id = "tenant-123"
    admin_user_id = "user-456"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db = AsyncMock()
    mock_db.execute = mock_execute

    svc = TenantInitializationService(mock_db)
    assert tenant_id not in svc._role_map

    with pytest.raises(ResourceNotFoundException) as exc_info:
        await svc.assign_admin_role(tenant_id, admin_user_id)

    assert exc_info.value.error_code == "RESOURCE_NOT_FOUND"
    assert exc_info.value.details["resource_type"] == "role"
    assert exc_info.value.details["resource_id"] == f"admin:{tenant_id}"
