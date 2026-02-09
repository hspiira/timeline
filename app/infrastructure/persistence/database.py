"""Persistence: async engine, session factory, and Base for SQLAlchemy ORM.

Schema is managed by Alembic migrations. Use get_db for read-only flows
and get_db_transactional for write operations (commit/rollback).
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.database_echo,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    query_cache_size=1200,
    connect_args=(
        {
            "server_settings": {"jit": "off"},
            "command_timeout": 60,
        }
        if "postgresql" in _settings.database_url
        else {}
    ),
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

    pass


async def get_db():
    """Database session dependency for read operations.

    Does not commit; use get_db_transactional for writes.
    Yields a session and closes it on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_transactional():
    """Database session dependency for write operations.

    Begins a transaction, commits on success, rolls back on exception.
    Use for POST, PUT, PATCH, DELETE endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                yield session
        except Exception:
            await session.rollback()
            raise
