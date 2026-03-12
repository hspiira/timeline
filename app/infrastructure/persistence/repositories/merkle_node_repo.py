"""Repository for MerkleNode persistence."""

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models import MerkleNode
from app.infrastructure.persistence.repositories.base import BaseRepository


class MerkleNodeRepository(BaseRepository[MerkleNode]):
    """Persistence operations for MerkleNode."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, MerkleNode)

    async def delete_for_epoch(self, epoch_id: str) -> None:
        """Delete all Merkle nodes for the given epoch."""
        await self.db.execute(
            self.model.__table__.delete().where(self.model.epoch_id == epoch_id)
        )

    async def get_leaf_nodes(
        self,
        epoch_id: str,
    ) -> list[MerkleNode]:
        """Return leaf nodes for epoch ordered by position."""
        result = await self.db.execute(
            select(MerkleNode)
            .where(MerkleNode.epoch_id == epoch_id, MerkleNode.event_seq.is_not(None))
            .order_by(asc(MerkleNode.position))
        )
        return list(result.scalars().all())

