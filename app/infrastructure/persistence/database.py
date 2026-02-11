"""Persistence: async engine, session factory, and Base for SQLAlchemy ORM.

When database_backend is 'postgres', schema is managed by Alembic migrations.
When database_backend is 'firestore', the SQL engine is not created; use
get_firestore_client() from app.infrastructure.firebase.client instead.

Engine and session factory are created lazily on first use (get_db /
get_db_transactional) so import does not trigger Settings validation.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.domain.exceptions import SqlNotConfiguredError

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


async def get_db():
    """Database session dependency for read operations.

    Does not commit; use get_db_transactional for writes.
    Yields a session and closes it on exit.
    Raises SqlNotConfiguredError when database_backend is not 'postgres'.
    """
    _ensure_engine()
    if AsyncSessionLocal is None:
        logger.error(
            "SQL database not configured: set DATABASE_BACKEND=postgres and DATABASE_URL "
            "(e.g. postgresql+asyncpg://user:pass@localhost:5432/dbname), then run: uv run alembic upgrade head"
        )
        raise SqlNotConfiguredError()
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_transactional():
    """Database session dependency for write operations.

    Begins a transaction, commits on success, rolls back on exception.
    Use for POST, PUT, PATCH, DELETE endpoints.
    Raises SqlNotConfiguredError when database_backend is not 'postgres'.
    """
    _ensure_engine()
    if AsyncSessionLocal is None:
        logger.error(
            "SQL database not configured: set DATABASE_BACKEND=postgres and DATABASE_URL "
            "(e.g. postgresql+asyncpg://user:pass@localhost:5432/dbname), then run: uv run alembic upgrade head"
        )
        raise SqlNotConfiguredError()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
