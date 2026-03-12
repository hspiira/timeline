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

    async def create_node(
        self,
        *,
        epoch_id: str,
        node_hash: str,
        depth: int,
        position: int,
        is_root: bool,
        left_child_hash: str | None = None,
        right_child_hash: str | None = None,
        event_seq: int | None = None,
    ) -> MerkleNode:
        """Insert a single Merkle node; the repository owns model construction."""
        node = MerkleNode(
            epoch_id=epoch_id,
            node_hash=node_hash,
            left_child_hash=left_child_hash,
            right_child_hash=right_child_hash,
            event_seq=event_seq,
            depth=depth,
            position=position,
            is_root=is_root,
        )
        return await self.create(node)

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

