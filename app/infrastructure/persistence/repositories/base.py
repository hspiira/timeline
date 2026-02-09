"""Base repository: generic CRUD and lifecycle hooks (cache invalidation)."""

from abc import ABC
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import object_session

from app.infrastructure.persistence.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """Base repository with get_by_id, get_all, create, update, delete and hooks.

    Subclasses override _on_after_create, _on_after_update, _on_before_delete
    for cache invalidation. LSP: subclasses are substitutable for BaseRepository.
    """

    def __init__(self, db: AsyncSession, model: type[ModelType]) -> None:
        self.db = db
        self.model = model

    async def get_by_id(self, id: str) -> ModelType | None:
        """Return a single record by primary key, or None."""
        model: Any = self.model
        result = await self.db.execute(select(self.model).where(model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Return records with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """Persist a new record and run _on_after_create hook."""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        await self._on_after_create(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        """Update an existing record (merge if detached) and run _on_after_update hook."""
        if object_session(obj) is None:
            obj = await self.db.merge(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        await self._on_after_update(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Run _on_before_delete hook then delete the record."""
        await self._on_before_delete(obj)
        await self.db.delete(obj)
        await self.db.flush()

    async def _on_after_create(self, obj: ModelType) -> None:
        """Override in subclasses to invalidate caches or emit events."""
        pass

    async def _on_after_update(self, obj: ModelType) -> None:
        """Override in subclasses to invalidate caches or emit events."""
        pass

    async def _on_before_delete(self, obj: ModelType) -> None:
        """Override in subclasses to invalidate caches or emit events."""
        pass
