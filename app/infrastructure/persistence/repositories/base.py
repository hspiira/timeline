"""Base repository: generic CRUD and lifecycle hooks (cache invalidation)."""

from typing import Any, cast

from sqlalchemy import and_, inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import object_session

from app.domain.exceptions import ResourceNotFoundException
from app.infrastructure.persistence.database import Base


class BaseRepository[ModelType: Base]:
    """Base repository: ORM-level CRUD and lifecycle hooks.

    The ``*_entity`` methods take and return ORM instances. Subclasses add their own
    domain-shaped methods (``get_by_id`` returning a DTO, ``create`` taking fields)
    alongside these rather than overriding them.

    Subclasses override _on_after_create, _on_after_update, _on_before_delete for
    cache invalidation.
    """

    def __init__(self, db: AsyncSession, model: type[ModelType]) -> None:
        self.db = db
        self.model = model

    async def get_entity_by_id(self, entity_id: str) -> ModelType | None:
        """Return a single ORM record by primary key, or None."""
        model: Any = self.model
        result = await self.db.execute(select(self.model).where(model.id == entity_id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Return records with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_entity(self, obj: ModelType) -> ModelType:
        """Persist a new ORM record and run _on_after_create hook."""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        await self._on_after_create(obj)
        return obj

    async def update_entity(
        self, obj: ModelType, *, skip_existence_check: bool = False
    ) -> ModelType:
        """Update an existing ORM record (merge if detached) and run _on_after_update hook.

        Verifies the record exists by primary key before merging; raises
        ResourceNotFoundException if any PK is missing or no row is found.
        When the object is already attached to this session, skips the existence
        SELECT to avoid a redundant query. When skip_existence_check is True,
        the existence SELECT is also skipped (use when the caller just loaded
        the entity in this session).
        """
        mapper = sa_inspect(self.model)
        # Mapped columns always have a key; the stub types it optional for the
        # unmapped Column case.
        pk_keys = [cast(str, col.key) for col in mapper.primary_key]
        for key in pk_keys:
            if getattr(obj, key) is None:
                raise ValueError(
                    f"Cannot update: primary key '{key}' is missing on "
                    f"{self.model.__name__} instance."
                )
        attached = object_session(obj) is self.db.sync_session
        if not attached and not skip_existence_check:
            stmt = select(self.model).where(
                and_(
                    *(getattr(self.model, k) == getattr(obj, k) for k in pk_keys)
                )
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                pk_str = ",".join(str(getattr(obj, k)) for k in pk_keys)
                raise ResourceNotFoundException(self.model.__name__, pk_str)
            obj = await self.db.merge(obj)
        elif not attached and skip_existence_check:
            obj = await self.db.merge(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        await self._on_after_update(obj)
        return obj

    async def delete_entity(self, obj: ModelType) -> None:
        """Run _on_before_delete hook then delete the ORM record."""
        await self._on_before_delete(obj)
        await self.db.delete(obj)
        await self.db.flush()

    async def _on_after_create(self, obj: ModelType) -> None:
        """Override in subclasses to invalidate caches or emit events."""

    async def _on_after_update(self, obj: ModelType) -> None:
        """Override in subclasses to invalidate caches or emit events."""

    async def _on_before_delete(self, obj: ModelType) -> None:
        """Override in subclasses to invalidate caches or emit events."""
