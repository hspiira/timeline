"""Merkle tree service for LEGAL_GRADE integrity profile."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from app.application.dtos.event import EventResult

if TYPE_CHECKING:
    from app.application.interfaces.repositories import IEventRepository


class IMerkleNodeRepository(Protocol):
    """Protocol for Merkle node persistence (create_node, delete_for_epoch)."""

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
    ) -> object: ...
    async def delete_for_epoch(self, epoch_id: str) -> None: ...


@dataclass(frozen=True)
class MerkleProofStep:
    """Single step in a Merkle proof path."""

    sibling_hash: str
    is_left_sibling: bool


class MerkleService:
    """Builds and stores Merkle trees per epoch and generates proofs."""

    def __init__(
        self,
        event_repo: IEventRepository,
        merkle_repo: IMerkleNodeRepository,
    ) -> None:
        self._event_repo = event_repo
        self._merkle_repo = merkle_repo

    async def build_and_store(self, tenant_id: str, epoch: object) -> str:
        """Build Merkle tree for all events in epoch and persist nodes (with child hashes).

        Args:
            tenant_id: Tenant id for the events.
            epoch: IntegrityEpoch ORM instance with id, tenant_id, terminal_hash, genesis_hash.

        Returns:
            Root hash of the Merkle tree.
        """
        events: list[EventResult] = await self._event_repo.get_events_for_epoch(
            tenant_id=tenant_id,
            epoch_id=epoch.id,
        )
        if not events:
            return epoch.terminal_hash or epoch.genesis_hash

        # Use merkle_leaf_hash when present; fall back to event hash.
        leaves: list[tuple[int, str]] = []
        for ev in events:
            if ev.event_seq is None:
                continue
            leaf_hash = ev.merkle_leaf_hash or ev.hash
            leaves.append((ev.event_seq, leaf_hash))

        if not leaves:
            return epoch.terminal_hash or epoch.genesis_hash

        leaves.sort(key=lambda p: p[0])

        await self._merkle_repo.delete_for_epoch(epoch.id)

        # Each element: (position, node_hash, left_child_hash, right_child_hash, event_seq|None).
        NodeRow = tuple[int, str, str | None, str | None, int | None]
        current_level: list[NodeRow] = [
            (idx, h, None, None, leaves[idx][0]) for idx, (_, h) in enumerate(leaves)
        ]
        levels: list[list[NodeRow]] = [current_level]

        while len(current_level) > 1:
            next_level: list[NodeRow] = []
            for i in range(0, len(current_level), 2):
                _, left_hash, _, _, _ = current_level[i]
                if i + 1 < len(current_level):
                    _, right_hash, _, _, _ = current_level[i + 1]
                else:
                    right_hash = left_hash
                combined = (left_hash + right_hash).encode("ascii")
                parent_hash = hashlib.sha256(combined).hexdigest()
                parent_pos = i // 2
                next_level.append((parent_pos, parent_hash, left_hash, right_hash, None))
            levels.append(next_level)
            current_level = next_level

        root_hash = levels[-1][0][1]
        depth_count = len(levels)

        for depth, level in enumerate(reversed(levels)):
            actual_depth = depth
            for position, node_hash, left_child_hash, right_child_hash, event_seq in level:
                is_root = actual_depth == 0
                await self._merkle_repo.create_node(
                    epoch_id=epoch.id,
                    node_hash=node_hash,
                    depth=actual_depth,
                    position=position,
                    is_root=is_root,
                    left_child_hash=left_child_hash,
                    right_child_hash=right_child_hash,
                    event_seq=event_seq,
                )

        return root_hash
