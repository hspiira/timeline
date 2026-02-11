"""Role application service: create role with optional permission assignments."""

from __future__ import annotations

from typing import Any

from app.application.dtos.role import RoleResult
from app.domain.exceptions import DuplicateAssignmentException


class RoleService:
    """Create roles and assign permissions in one transaction."""

    def __init__(
        self,
        role_repo: Any,
        permission_repo: Any,
        role_permission_repo: Any,
    ) -> None:
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo

    async def create_role_with_permissions(
        self,
        tenant_id: str,
        code: str,
        name: str,
        description: str | None = None,
        permission_codes: list[str] | None = None,
    ) -> RoleResult:
        """Create role and optionally assign permissions by code.

        Raises:
            ValueError: If role with code already exists or a permission code is invalid.
        """
        existing = await self._role_repo.get_by_code_and_tenant(code, tenant_id)
        if existing:
            raise ValueError(f"Role with code '{code}' already exists")
        created = await self._role_repo.create_role(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description,
        )
        if permission_codes:
            for perm_code in permission_codes:
                perm = await self._permission_repo.get_by_code_and_tenant(
                    perm_code, tenant_id
                )
                if not perm:
                    raise ValueError(f"Invalid permission code: {perm_code}")
                try:
                    await self._role_permission_repo.assign_permission_to_role(
                        role_id=created.id,
                        permission_id=perm.id,
                        tenant_id=tenant_id,
                    )
                except DuplicateAssignmentException:
                    pass
        return created
