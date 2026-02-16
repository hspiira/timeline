"""Persistence: async engine, session factory, and Base for SQLAlchemy ORM.

When database_backend is 'postgres', schema is managed by Alembic migrations.
When database_backend is 'firestore', the SQL engine is not created; use
get_firestore_client() from app.infrastructure.firebase.client instead.

Engine and session factory are created lazily on first use (get_db /
get_db_transactional) so import does not trigger Settings validation.

When RLS is enabled, get_db and get_db_transactional set app.current_tenant_id
from the tenant context (set by TenantContextMiddleware) so row-level security
policies restrict rows to the current tenant.
"""

import logging
import re
from typing import Any

# Strict format for tenant_id before interpolation into SET LOCAL (CUID/UUID-style).
_TENANT_ID_MAX_LENGTH = 64
_TENANT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1," + str(_TENANT_ID_MAX_LENGTH) + r"}$")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.tenant_context import get_tenant_id as get_current_tenant_id
from app.domain.exceptions import SqlNotConfiguredException

logger = logging.getLogger(__name__)

# Set by _ensure_engine() on first use; avoids get_settings() at import time.
engine: Any = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> None:
    """Create engine and AsyncSessionLocal on first use (postgres only)."""
    global engine, AsyncSessionLocal
    if AsyncSessionLocal is not None:
        return
    settings = get_settings()
    if settings.database_backend != "postgres":
        return
    pool_size = settings.db_pool_size if settings.db_pool_size is not None else 20
    max_overflow = (
        settings.db_max_overflow if settings.db_max_overflow is not None else 30
    )
    query_cache_size = (
        settings.db_query_cache_size
        if settings.db_query_cache_size is not None
        else 1200
    )
    command_timeout = (
        settings.db_command_timeout
        if settings.db_command_timeout is not None
        else 60
    )
    connect_args: dict[str, Any] = {}
    if "postgresql" in settings.database_url:
        connect_args["command_timeout"] = command_timeout
        if settings.db_disable_jit:
            connect_args["server_settings"] = {"jit": "off"}
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=3600,
        query_cache_size=query_cache_size,
        connect_args=connect_args,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""


def _quote_set_value(value: str) -> str:
    """Escape a value for use in PostgreSQL SET (single-quoted literal)."""
    return value.replace("'", "''")


def _is_valid_tenant_id_for_set_local(value: str) -> bool:
    """Return True if value is safe to interpolate into SET LOCAL (format + length)."""
    if not value or len(value) > _TENANT_ID_MAX_LENGTH:
        return False
    return bool(_TENANT_ID_RE.fullmatch(value))


async def _set_tenant_context(session: AsyncSession) -> None:
    """Set app.current_tenant_id on the session for RLS (when tenant context is set).

    SET LOCAL does not support bound parameters in PostgreSQL; the value must be
    interpolated. We validate format (CUID/UUID-style, max length) and escape
    single quotes. If validation fails, we skip SET LOCAL and log.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return
    if not _is_valid_tenant_id_for_set_local(tenant_id):
        logger.warning(
            "Skipping SET LOCAL app.current_tenant_id: tenant_id failed format validation (length=%d, max=%d)",
            len(tenant_id),
            _TENANT_ID_MAX_LENGTH,
        )
        return
    safe = _quote_set_value(tenant_id)
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{safe}'"))


async def get_db():
    """Database session dependency for read operations.

    Does not commit; use get_db_transactional for writes.
    When tenant context is set (middleware), runs SET LOCAL app.current_tenant_id for RLS.
    Yields a session and closes it on exit.
    Raises SqlNotConfiguredException when database_backend is not 'postgres'.
    """
    _ensure_engine()
    if AsyncSessionLocal is None:
        logger.error(
            "SQL database not configured: set DATABASE_BACKEND=postgres and DATABASE_URL "
            "(e.g. postgresql+asyncpg://user:pass@localhost:5432/dbname), then run: uv run alembic upgrade head"
        )
        raise SqlNotConfiguredException()
    async with AsyncSessionLocal() as session:
        await _set_tenant_context(session)
        yield session


async def get_db_transactional():
    """Database session dependency for write operations.

    Begins a transaction, commits on success, rolls back on exception.
    When tenant context is set (middleware), runs SET LOCAL app.current_tenant_id for RLS.
    Use for POST, PUT, PATCH, DELETE endpoints.
    Raises SqlNotConfiguredException when database_backend is not 'postgres'.
    """
    _ensure_engine()
    if AsyncSessionLocal is None:
        logger.error(
            "SQL database not configured: set DATABASE_BACKEND=postgres and DATABASE_URL "
            "(e.g. postgresql+asyncpg://user:pass@localhost:5432/dbname), then run: uv run alembic upgrade head"
        )
        raise SqlNotConfiguredException()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _set_tenant_context(session)
            yield session
