"""Permission application service: create with duplicate check."""

from __future__ import annotations

from app.application.dtos.permission import PermissionResult
from app.application.interfaces.repositories import IPermissionRepository
from app.domain.exceptions import ValidationException

_MSG_DUPLICATE_PERMISSION = "Permission with code '%s' already exists"


class PermissionService:
    """Create permissions with validation."""

    def __init__(self, permission_repo: IPermissionRepository) -> None:
        self._repo = permission_repo

    async def create_permission(
        self,
        tenant_id: str,
        code: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> PermissionResult:
        """Create permission. Raises ValidationException if code already exists for tenant."""
        # Duplicate check is best-effort; TOCTOU race is possible. The API endpoint catches
        # IntegrityError as a fallback, so concurrent creates still return 400 (layered defense).
        existing = await self._repo.get_by_code_and_tenant(code, tenant_id)
        if existing:
            raise ValidationException(_MSG_DUPLICATE_PERMISSION % code)
        return await self._repo.create_permission(
            tenant_id=tenant_id,
            code=code,
            resource=resource,
            action=action,
            description=description,
        )
