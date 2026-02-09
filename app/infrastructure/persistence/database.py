"""Persistence: async engine, session factory, and Base for SQLAlchemy ORM.

When database_backend is 'postgres', schema is managed by Alembic migrations.
When database_backend is 'firestore', the SQL engine is not created; use
get_firestore_client() from app.infrastructure.firebase.client instead.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

# Only create SQL engine when using PostgreSQL; Firestore uses Firebase client.
if _settings.database_backend == "postgres":
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
else:
    engine = None
    AsyncSessionLocal = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


async def get_db():
    """Database session dependency for read operations.

    Does not commit; use get_db_transactional for writes.
    Yields a session and closes it on exit.
    Raises RuntimeError when database_backend is not 'postgres'.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "SQL database is not configured (database_backend is not 'postgres'). "
            "Use get_firestore_client() from app.infrastructure.firebase.client for Firestore."
        )
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_transactional():
    """Database session dependency for write operations.

    Begins a transaction, commits on success, rolls back on exception.
    Use for POST, PUT, PATCH, DELETE endpoints.
    Raises RuntimeError when database_backend is not 'postgres'.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "SQL database is not configured (database_backend is not 'postgres'). "
            "Use get_firestore_client() from app.infrastructure.firebase.client for Firestore."
        )
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                yield session
        except Exception:
            await session.rollback()
            raise
