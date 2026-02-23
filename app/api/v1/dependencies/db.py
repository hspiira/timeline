"""DB and audit service dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hash_service import HashService
from app.infrastructure.persistence.database import get_db_transactional
from app.infrastructure.persistence.repositories import (
    PasswordSetTokenStore,
    UserRepository,
)
from app.infrastructure.services import SystemAuditService


async def get_system_audit_service(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> SystemAuditService:
    """Build SystemAuditService for Postgres write path (same session as request)."""
    return SystemAuditService(db, HashService())


async def get_set_password_deps(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> tuple[PasswordSetTokenStore, UserRepository]:
    """Token store and user repo for POST /auth/set-initial-password (same transaction)."""
    audit_svc = SystemAuditService(db, HashService())
    return (PasswordSetTokenStore(db), UserRepository(db, audit_service=audit_svc))
