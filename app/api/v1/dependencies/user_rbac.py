"""User, RBAC (roles/permissions), and auth dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserResult
from app.application.services.authorization_service import AuthorizationService
from app.application.services.permission_service import PermissionService
from app.application.services.role_service import RoleService
from app.application.services.user_service import UserService
from app.core.config import get_settings
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.repositories import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from app.infrastructure.services import SystemAuditService

from . import auth
from . import tenant
from . import db as db_deps


_http_bearer = HTTPBearer(auto_error=False)


def _to_user_result(user: User | UserResult) -> UserResult:
    """Normalize repo result (ORM User or UserResult) to UserResult for consistent typing."""
    if isinstance(user, UserResult):
        return user
    return UserResult(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
    )


async def get_user_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    """User repository for read operations (list, get by id, lookup by username).

    Args:
        db: Async session from Depends(get_db). Audit logging disabled for reads.

    Returns:
        UserRepository instance with audit_service=None for read-only use.
    """
    return UserRepository(db, audit_service=None)


async def get_user_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> UserRepository:
    """User repository for create/update/delete (transactional, with audit).

    Args:
        db: Async session from Depends(get_db_transactional).
        audit_svc: Injected system audit service for write logging.

    Returns:
        UserRepository instance wired for transactional writes and audit.
    """
    return UserRepository(db, audit_service=audit_svc)


async def get_authorization_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthorizationService:
    """Build AuthorizationService with permission resolver and optional cache.

    Cache is set in app lifespan (app.state.cache) when Redis is enabled;
    otherwise cache is None and permission checks hit the DB only.

    Args:
        request: Incoming request; app.state.cache used when present.
        db: Async session from Depends(get_db) for permission resolver.

    Returns:
        AuthorizationService wired with PermissionResolver and optional cache.
    """
    from app.infrastructure.services import PermissionResolver

    settings = get_settings()
    permission_resolver = PermissionResolver(db)
    cache = getattr(request.app.state, "cache", None)
    return AuthorizationService(
        permission_resolver=permission_resolver,
        cache=cache,
        cache_ttl=settings.cache_ttl_permissions,
    )


async def get_role_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleRepository:
    """Role repository for read operations (list, get by id).

    Args:
        db: Async session from Depends(get_db). Audit logging disabled for reads.

    Returns:
        RoleRepository instance with audit_service=None for read-only use.
    """
    return RoleRepository(db, audit_service=None)


async def get_role_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> RoleRepository:
    """Role repository for create/update/delete (transactional, with audit).

    Args:
        db: Async session from Depends(get_db_transactional).
        audit_svc: Injected system audit service for write logging.

    Returns:
        RoleRepository instance wired for transactional writes and audit.
    """
    return RoleRepository(db, audit_service=audit_svc)


async def get_permission_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionRepository:
    """Permission repository for read operations and user/role assignment.

    Args:
        db: Async session from Depends(get_db). Audit logging disabled for reads.

    Returns:
        PermissionRepository instance with audit_service=None for read-only use.
    """
    return PermissionRepository(db, audit_service=None)


async def get_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> PermissionRepository:
    """Permission repository for create/update/delete (transactional, with audit).

    Args:
        db: Async session from Depends(get_db_transactional).
        audit_svc: Injected system audit service for write logging.

    Returns:
        PermissionRepository instance wired for transactional writes and audit.
    """
    return PermissionRepository(db, audit_service=audit_svc)


async def get_role_permission_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RolePermissionRepository:
    """Role-permission repository for read (e.g. get_permissions_for_role).

    Args:
        db: Async session from Depends(get_db). Audit logging disabled for reads.

    Returns:
        RolePermissionRepository instance with audit_service=None for read-only use.
    """
    return RolePermissionRepository(db, audit_service=None)


async def get_role_permission_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> RolePermissionRepository:
    """Role-permission repository for assign/remove (transactional, with audit).

    Args:
        db: Async session from Depends(get_db_transactional).
        audit_svc: Injected system audit service for write logging.

    Returns:
        RolePermissionRepository instance wired for transactional writes and audit.
    """
    return RolePermissionRepository(db, audit_service=audit_svc)


async def get_user_role_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRoleRepository:
    """User-role repository for read (e.g. get_user_roles).

    Args:
        db: Async session from Depends(get_db). Audit logging disabled for reads.

    Returns:
        UserRoleRepository instance with audit_service=None for read-only use.
    """
    return UserRoleRepository(db, audit_service=None)


async def get_user_role_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(db_deps.get_system_audit_service)],
) -> UserRoleRepository:
    """User-role repository for assign/remove (transactional, with audit).

    Args:
        db: Async session from Depends(get_db_transactional).
        audit_svc: Injected system audit service for write logging.

    Returns:
        UserRoleRepository instance wired for transactional writes and audit.
    """
    return UserRoleRepository(db, audit_service=audit_svc)


def get_role_service(
    role_repo: Annotated[RoleRepository, Depends(get_role_repo_for_write)],
    permission_repo: Annotated[PermissionRepository, Depends(get_permission_repo)],
    role_permission_repo: Annotated[
        RolePermissionRepository, Depends(get_role_permission_repo_for_write)
    ],
) -> RoleService:
    """Role service for create-with-permissions (composition root).

    Args:
        role_repo: Role repository for writes (transactional).
        permission_repo: Permission repository for read/resolve.
        role_permission_repo: Role-permission repository for assign/remove.

    Returns:
        RoleService instance for role CRUD and permission assignment.
    """
    return RoleService(
        role_repo=role_repo,
        permission_repo=permission_repo,
        role_permission_repo=role_permission_repo,
    )


def get_permission_service(
    permission_repo: Annotated[
        PermissionRepository, Depends(get_permission_repo_for_write)
    ],
) -> PermissionService:
    """Permission service for permission CRUD (composition root).

    Args:
        permission_repo: Permission repository for writes (transactional).

    Returns:
        PermissionService instance for permission management.
    """
    return PermissionService(permission_repo=permission_repo)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo_for_write)],
    auth_security: Annotated[auth.AuthSecurity, Depends(auth.get_auth_security)],
) -> UserService:
    """User service for update-me and password change (composition root).

    Args:
        user_repo: User repository for writes (transactional).
        auth_security: Auth token and password hashing dependency.

    Returns:
        UserService instance for user self-service operations.
    """
    return UserService(user_repo=user_repo, auth_security=auth_security)


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserResult | None:
    """Return current user from JWT if present; else None.

    Use for optional-auth routes. Does not raise on missing or invalid token.

    Args:
        credentials: Bearer token from request; None if absent.
        user_repo: User repository to load user by id and tenant.

    Returns:
        UserResult if valid JWT and active user, else None.
    """
    if not credentials:
        return None
    try:
        from app.infrastructure.security.jwt import verify_token

        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            return None
        user = await user_repo.get_by_id_and_tenant(user_id, tenant_id)
        if not user or not user.is_active:
            return None
        return _to_user_result(user)
    except (ValueError, KeyError):
        return None


async def get_current_user(
    current_user: Annotated[UserResult | None, Depends(get_current_user_optional)],
) -> UserResult:
    """Return current user from JWT; raise 401 if missing or invalid.

    Args:
        current_user: Result of get_current_user_optional (None if not authenticated).

    Returns:
        UserResult for the authenticated user.

    Raises:
        HTTPException: 401 if current_user is None.
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


def require_permission(resource: str, action: str):
    """Dependency factory: require JWT auth and that the user has resource:action."""

    async def _require(
        current_user: Annotated[UserResult, Depends(get_current_user)],
        tenant_id: Annotated[str, Depends(tenant.get_tenant_id)],
        auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> UserResult:
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        await auth_svc.require_permission(
            current_user.id, tenant_id, resource, action
        )
        return current_user

    return _require
