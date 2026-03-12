"""Merkle tree service for LEGAL_GRADE integrity profile."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from app.application.dtos.event import EventResult

if TYPE_CHECKING:
    from app.application.interfaces.repositories import IEventRepository


class MerkleNodeView(Protocol):
    """Structural view of a Merkle node for proof traversal (depth, position, child hashes)."""

    depth: int
    position: int
    left_child_hash: str | None
    right_child_hash: str | None


# (position, node_hash, left_child_hash, right_child_hash, event_seq|None) per level in build.
NodeRow = tuple[int, str, str | None, str | None, int | None]


class IMerkleNodeRepository(Protocol):
    """Protocol for Merkle node persistence and proof path lookup."""

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
    async def get_leaf_by_event_seq(
        self, epoch_id: str, event_seq: int
    ) -> MerkleNodeView | None: ...
    async def get_node(
        self, epoch_id: str, depth: int, position: int
    ) -> MerkleNodeView | None: ...


@dataclass(frozen=True)
class MerkleProofStep:
    """Single step in a Merkle proof path."""

    sibling_hash: str
    is_left_sibling: bool


class MerkleService:
    """Builds and stores Merkle trees per epoch and generates proofs.

    Proof path is sibling hashes from leaf to root so a verifier can
    recompute the root (see docs/chain_integrity_architecture.md).
    """

    def __init__(
        self,
        event_repo: IEventRepository,
        merkle_repo: IMerkleNodeRepository,
    ) -> None:
        self._event_repo = event_repo
        self._merkle_repo = merkle_repo

    async def generate_proof(
        self, epoch_id: str, event_seq: int
    ) -> list[MerkleProofStep]:
        """Return sibling path from leaf to root for the given event in the epoch.

        Verifier hashes leaf with sibling (order from is_left_sibling), then
        repeats with each step to recompute the root.

        Issues one DB round-trip per tree level (O(log N)); could be batched
        with a single query over (depth, position) pairs for large trees.

        Args:
            epoch_id: Integrity epoch id.
            event_seq: Event sequence number in that epoch.

        Returns:
            List of proof steps (sibling hash and side). Empty if no leaf for
            event_seq or tree not built.

        Raises:
            LookupError: If a parent node is missing (incomplete tree).
            ValueError: If a parent has missing child hash (data corruption).
        """
        leaf = await self._merkle_repo.get_leaf_by_event_seq(epoch_id, event_seq)
        if leaf is None:
            return []
        # Stored tree: depth 0 = root, max depth = leaves (see build_and_store).
        current_depth = leaf.depth
        current_pos = leaf.position
        path: list[MerkleProofStep] = []
        while current_depth > 0:
            parent_depth = current_depth - 1
            parent_pos = current_pos // 2
            parent = await self._merkle_repo.get_node(
                epoch_id, parent_depth, parent_pos
            )
            if parent is None:
                raise LookupError(
                    f"Merkle tree incomplete: node missing at depth={parent_depth}, "
                    f"position={parent_pos} (epoch_id={epoch_id!r})"
                )
            left_ch = parent.left_child_hash
            right_ch = parent.right_child_hash
            if current_pos % 2 == 0:
                sibling_hash = right_ch
                is_left_sibling = False
            else:
                sibling_hash = left_ch
                is_left_sibling = True
            if sibling_hash is None:
                raise ValueError(
                    f"Merkle node at depth={parent_depth}, position={parent_pos} "
                    f"(epoch_id={epoch_id!r}) has missing child hash"
                )
            path.append(
                MerkleProofStep(sibling_hash=sibling_hash, is_left_sibling=is_left_sibling)
            )
            current_depth = parent_depth
            current_pos = parent_pos
        return path

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

        for depth, level in enumerate(reversed(levels)):
            for position, node_hash, left_child_hash, right_child_hash, event_seq in level:
                is_root = depth == 0
                await self._merkle_repo.create_node(
                    epoch_id=epoch.id,
                    node_hash=node_hash,
                    depth=depth,
                    position=position,
                    is_root=is_root,
                    left_child_hash=left_child_hash,
                    right_child_hash=right_child_hash,
                    event_seq=event_seq,
                )

        return root_hash
