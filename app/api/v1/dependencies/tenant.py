"""Tenant-related dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.tenant_creation_service import TenantCreationService
from app.core.config import get_settings
from app.core.tenant_validation import is_valid_tenant_id_format
from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import (
    PasswordSetTokenStore,
    TenantRepository,
    UserRepository,
)
from app.infrastructure.services import SystemAuditService, TenantInitializationService
from app.application.services.hash_service import HashService

from .common import TENANT_CACHE_MISS_MARKER, TENANT_VALIDATION_CACHE_TTL


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
