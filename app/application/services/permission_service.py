"""Permission application service: create with duplicate check."""

from __future__ import annotations

from typing import Any

from app.domain.exceptions import ValidationException


class PermissionService:
    """Create permissions with validation."""

    def __init__(self, permission_repo: Any) -> None:
        self._repo = permission_repo

    async def create_permission(
        self,
        tenant_id: str,
        code: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> Any:
        """Create permission. Raises ValidationException if code already exists for tenant."""
        existing = await self._repo.get_by_code_and_tenant(code, tenant_id)
        if existing:
            raise ValidationException(f"Permission with code '{code}' already exists")
        return await self._repo.create_permission(
            tenant_id=tenant_id,
            code=code,
            resource=resource,
            action=action,
            description=description,
        )
