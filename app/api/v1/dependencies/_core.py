"""Auth, user/RBAC, tenant, audit, and infrastructure dependencies (composition root).

Infrastructure-level FastAPI Depends() factories: sessions, tokens, permissions,
tenant resolution, audit logging, and email/OAuth credentials.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserResult
from app.application.services.enrichment import EnrichmentContext
from app.application.services.authorization_service import AuthorizationService
from app.application.services.rate_limiter import IRateLimiter
from app.application.services.hash_service import HashService
from app.application.services.permission_service import PermissionService
from app.application.services.role_service import RoleService
from app.application.services.tenant_creation_service import TenantCreationService
from app.application.services.user_service import UserService
from app.core.config import get_settings
from app.core.tenant_validation import is_valid_tenant_id_format
from app.infrastructure.external.email.encryption import CredentialEncryptor
from app.infrastructure.external.email.envelope_encryption import (
    EnvelopeEncryptor,
    OAuthStateManager,
)
from app.infrastructure.external.email.oauth_drivers import OAuthDriverRegistry
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.repositories import (
    AuditLogRepository,
    EmailAccountRepository,
    OAuthProviderConfigRepository,
    OAuthStateRepository,
    PasswordSetTokenStore,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    TenantRepository,
    UserRepository,
    UserRoleRepository,
)
from app.infrastructure.persistence.rls_check import RLSCheckResult, run_rls_check
from app.infrastructure.security.jwt import create_access_token, verify_token
from app.infrastructure.security.password import get_password_hash
from app.infrastructure.services import SystemAuditService, TenantInitializationService
from app.infrastructure.services.api_audit_log_service import ApiAuditLogService
from app.infrastructure.services.email_account_service import EmailAccountService
from app.infrastructure.services.oauth_config_service import OAuthConfigService
from app.shared.request_audit import (
    get_audit_action_from_method,
    get_audit_payload,
    get_audit_request_context,
    get_audit_resource_from_path,
    get_tenant_and_user_for_audit,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (formerly common.py)
# ---------------------------------------------------------------------------

TENANT_VALIDATION_CACHE_TTL: int = 60
TENANT_CACHE_MISS_MARKER: str = "__missing__"


# ---------------------------------------------------------------------------
# Health / readiness (formerly health.py)
# ---------------------------------------------------------------------------

async def get_rls_readiness_result() -> RLSCheckResult:
    """Compute RLS readiness result from settings for the readiness probe.

    When RLS_READINESS_CHECK is False, returns ok=True without running checks.
    Otherwise runs run_rls_check with database_url, app_role (from settings or
    derived from database_url username), and check_policies flag.

    Returns:
        RLSCheckResult with ok=True if ready, ok=False and message otherwise.
    """
    settings = get_settings()
    if not settings.rls_readiness_check:
        return RLSCheckResult(ok=True, message="RLS check disabled")

    app_role = settings.rls_check_app_role
    if not app_role and settings.database_url:
        parsed = urlparse(settings.database_url)
        app_role = parsed.username

    return await run_rls_check(
        database_url=settings.database_url,
        app_role=app_role,
        migrator_role=None,
        check_policies=settings.rls_check_policies,
    )


# ---------------------------------------------------------------------------
# System audit / set-password (formerly db.py)
# ---------------------------------------------------------------------------

async def get_system_audit_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SystemAuditService:
    """Build SystemAuditService for Postgres write path (same session as request)."""
    return SystemAuditService(db, HashService())


async def get_set_password_deps(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> tuple[PasswordSetTokenStore, UserRepository]:
    """Token store and user repo for POST /auth/set-initial-password (same transaction)."""
    return (PasswordSetTokenStore(db), UserRepository(db, audit_service=audit_svc))


# ---------------------------------------------------------------------------
# Audit log (formerly audit.py)
# ---------------------------------------------------------------------------

async def get_audit_log_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogRepository:
    """Audit log repository for read operations (list entries).

    Writes are performed by ensure_audit_logged in the same transaction as the
    route mutation. Use this dependency for read-only audit log access.

    Args:
        db: Database session for read operations.

    Returns:
        AuditLogRepository instance bound to the session.
    """
    return AuditLogRepository(db)


async def ensure_audit_logged(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> AsyncIterator[None]:
    """Write API audit log in the same transaction when the route completes.

    Add to write endpoints (POST/PUT/PATCH/DELETE) so the audit row is committed
    in the same transaction as the mutation. If the route raises, the transaction
    rolls back and no audit row is written.

    Args:
        request: Incoming request used to derive audit context (tenant, user,
            resource, action, IP, user-agent).
        db: Transactional database session for audit persistence.

    Yields:
        None. Audit log is written after the route returns successfully.
    """
    yield
    # After route returned normally: write audit in same transaction before commit.
    tenant_id, user_id = get_tenant_and_user_for_audit(request)
    if not tenant_id:
        return
    resource_type, resource_id = get_audit_resource_from_path(request.url.path)
    if not resource_type:
        return
    request_id, ip_address, user_agent = get_audit_request_context(request)
    action = get_audit_action_from_method(request.method)
    old_values, new_values = get_audit_payload(request)
    try:
        svc = ApiAuditLogService(db)
        await svc.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
            error_message=None,
        )
    except Exception:
        logger.exception(
            "Audit log write failed; mutation committed without audit record. "
            "resource=%s resource_id=%s action=%s tenant_id=%s user_id=%s",
            resource_type,
            resource_id,
            action,
            tenant_id,
            user_id,
        )


# ---------------------------------------------------------------------------
# Tenant (formerly tenant.py)
# ---------------------------------------------------------------------------

async def get_tenant_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantRepository:
    """Tenant repository for read operations."""
    return TenantRepository(db, cache_service=None, audit_service=None)


async def get_tenant_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> TenantRepository:
    """Tenant repository for writes (transactional)."""
    audit_svc = SystemAuditService(db, HashService())
    return TenantRepository(db, cache_service=None, audit_service=audit_svc)


async def get_tenant_id(
    request: Request,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repo)],
) -> str:
    """Resolve tenant ID from header and validate it exists.

    Uses app.state.cache (short TTL) when available to avoid hitting the tenant
    repository on every request.
    """
    name = get_settings().tenant_header_name
    value = request.headers.get(name)
    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {name}",
        )
    if not is_valid_tenant_id_format(value):
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant ID format (use alphanumeric, hyphen, underscore; max 64 characters)",
        )
    cache = getattr(request.app.state, "cache", None)
    cache_key = f"tenant:{value}"
    if cache and cache.is_available():
        cached = await cache.get(cache_key)
        if cached is not None:
            if cached == TENANT_CACHE_MISS_MARKER:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or unknown tenant",
                )
            return value
    tenant = await tenant_repo.get_by_id(value)
    if not tenant:
        if cache and cache.is_available():
            await cache.set(
                cache_key, TENANT_CACHE_MISS_MARKER, ttl=TENANT_VALIDATION_CACHE_TTL
            )
        raise HTTPException(
            status_code=400,
            detail="Invalid or unknown tenant",
        )
    if cache and cache.is_available():
        await cache.set(cache_key, value, ttl=TENANT_VALIDATION_CACHE_TTL)
    return value


def get_verified_tenant_id(
    tenant_id: str,
    tenant_id_header: Annotated[str, Depends(get_tenant_id)],
) -> str:
    """Ensure path tenant_id matches X-Tenant-ID header; return tenant_id or raise 403."""
    if tenant_id != tenant_id_header:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tenant_id


async def get_tenant_creation_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> TenantCreationService:
    """Build TenantCreationService (Postgres)."""
    audit_svc = SystemAuditService(db, HashService())
    token_store = PasswordSetTokenStore(db)
    return TenantCreationService(
        tenant_repo=TenantRepository(db),
        user_repo=UserRepository(db, audit_service=audit_svc),
        init_service=TenantInitializationService(db),
        audit_service=audit_svc,
        token_store=token_store,
    )


# ---------------------------------------------------------------------------
# Auth (formerly auth.py)
# ---------------------------------------------------------------------------

def get_create_access_token():
    """Dependency: JWT access token builder (no direct infra import in routes)."""
    return create_access_token


def get_password_hash_dependency():
    """Dependency: password hashing for storage (no direct infra import in routes)."""
    return get_password_hash


def get_credential_encryptor() -> CredentialEncryptor:
    """Credential encryptor for email account credentials.

    Returns:
        CredentialEncryptor instance for encrypting/decrypting stored credentials.
    """
    return CredentialEncryptor()


def get_envelope_encryptor() -> EnvelopeEncryptor:
    """Envelope encryptor for OAuth client secrets.

    Returns:
        EnvelopeEncryptor instance for encrypting/decrypting OAuth secrets.
    """
    return EnvelopeEncryptor()


def get_oauth_state_manager() -> OAuthStateManager:
    """OAuth state signing and verification for authorize/callback flows.

    Returns:
        OAuthStateManager instance for signing and verifying state parameters.
    """
    return OAuthStateManager()


def get_oauth_driver_registry(request: Request) -> OAuthDriverRegistry:
    """OAuth driver registry with shared HTTP client from app state.

    Args:
        request: Incoming request; app.state.oauth_http_client is used when set.

    Returns:
        OAuthDriverRegistry configured with the shared HTTP client.
    """
    http_client = getattr(request.app.state, "oauth_http_client", None)
    return OAuthDriverRegistry(http_client=http_client)


# ---------------------------------------------------------------------------
# User / RBAC (formerly user_rbac.py)
# ---------------------------------------------------------------------------

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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
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
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
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
    hash_password: Annotated[
        Callable[[str], str],
        Depends(get_password_hash_dependency),
    ],
) -> UserService:
    """User service for update-me and password change (composition root).

    Args:
        user_repo: User repository for writes (transactional).
        hash_password: Password hashing callable for storage.

    Returns:
        UserService instance for user self-service operations.
    """
    return UserService(user_repo=user_repo, hash_password=hash_password)


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


async def check_event_rate_limit(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> None:
    """Raise 429 if event create rate limit exceeded for this tenant. Wire on POST /events."""
    limiter: IRateLimiter | None = getattr(request.app.state, "event_rate_limiter", None)
    if limiter is None:
        return
    settings = get_settings()
    allowed = await limiter.check(
        key=f"events:{tenant_id}",
        limit=settings.rate_limit_events_per_minute_per_tenant,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Event rate limit exceeded",
        )


async def get_event_create_rate_limit(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> None:
    """Alias for check_event_rate_limit. Raise 429 if event create rate limit exceeded for this tenant."""
    await check_event_rate_limit(request, tenant_id)


async def get_event_bulk_rate_limit(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> None:
    """Raise 429 if bulk event create rate limit exceeded for this tenant. Wire on POST /events/bulk."""
    limiter: IRateLimiter | None = getattr(request.app.state, "event_rate_limiter", None)
    if limiter is None:
        return
    settings = get_settings()
    key = f"event:bulk:{tenant_id}"
    allowed = await limiter.check(
        key,
        settings.rate_limit_bulk_events_per_minute_per_tenant,
        60,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many bulk event creations for this tenant; try again later",
        )


async def get_enrichment_context(
    request: Request,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    current_user: Annotated[UserResult | None, Depends(get_current_user_optional)],
) -> EnrichmentContext:
    """Build enrichment context from request (for API-originated events)."""
    settings = get_settings()
    request_id = request.headers.get(settings.request_id_header)
    source_ip = request.client.host if request.client else None
    actor_id = current_user.id if current_user else None
    return EnrichmentContext(
        tenant_id=tenant_id,
        actor_id=actor_id,
        request_id=request_id,
        source_ip=source_ip,
    )


def require_permission(resource: str, action: str):
    """Dependency factory: require JWT auth and that the user has resource:action."""

    async def _require(
        current_user: Annotated[UserResult, Depends(get_current_user)],
        tenant_id: Annotated[str, Depends(get_tenant_id)],
        auth_svc: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> UserResult:
        if current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        await auth_svc.require_permission(
            current_user.id, tenant_id, resource, action
        )
        return current_user

    return _require


# Named permission dependencies (composition root: routes use Depends(get_*))
get_chain_anchor_read_permission = require_permission("chain_anchor", "read")
get_system_read_permission = require_permission("system", "read")
get_webhook_read_permission = require_permission("webhook", "read")
get_webhook_write_permission = require_permission("webhook", "write")
get_projection_read_permission = require_permission("projection", "read")
get_projection_write_permission = require_permission("projection", "write")


# ---------------------------------------------------------------------------
# OAuth provider config and email accounts (formerly oauth_email.py)
# ---------------------------------------------------------------------------

async def get_oauth_provider_config_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for read operations."""
    return OAuthProviderConfigRepository(db, audit_service=None)


async def get_oauth_provider_config_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    audit_svc: Annotated[SystemAuditService, Depends(get_system_audit_service)],
) -> OAuthProviderConfigRepository:
    """OAuth provider config repository for create/update/delete (transactional)."""
    return OAuthProviderConfigRepository(db, audit_service=audit_svc)


async def get_oauth_state_repo(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
    state_manager: Annotated[OAuthStateManager, Depends(get_oauth_state_manager)],
) -> OAuthStateRepository:
    """OAuth state repository for authorize/callback (transactional)."""
    return OAuthStateRepository(db, state_manager=state_manager)


async def get_email_account_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailAccountRepository:
    """Email account repository for read operations (list, get by id)."""
    return EmailAccountRepository(db)


async def get_email_account_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> EmailAccountRepository:
    """Email account repository for create/update/delete (transactional)."""
    return EmailAccountRepository(db)


async def get_oauth_config_service(
    oauth_repo: Annotated[
        OAuthProviderConfigRepository, Depends(get_oauth_provider_config_repo_for_write)
    ],
    state_repo: Annotated[OAuthStateRepository, Depends(get_oauth_state_repo)],
    envelope_encryptor: Annotated[EnvelopeEncryptor, Depends(get_envelope_encryptor)],
    driver_registry: Annotated[OAuthDriverRegistry, Depends(get_oauth_driver_registry)],
) -> OAuthConfigService:
    """OAuth config and flow service (composition root)."""
    return OAuthConfigService(
        oauth_repo=oauth_repo,
        state_repo=state_repo,
        envelope_encryptor=envelope_encryptor,
        driver_registry=driver_registry,
    )


async def get_email_account_service(
    email_account_repo: Annotated[
        EmailAccountRepository, Depends(get_email_account_repo_for_write)
    ],
    credential_encryptor: Annotated[
        CredentialEncryptor, Depends(get_credential_encryptor)
    ],
) -> EmailAccountService:
    """Email account service (composition root)."""
    return EmailAccountService(
        email_account_repo=email_account_repo,
        credential_encryptor=credential_encryptor,
    )
