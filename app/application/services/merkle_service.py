"""Merkle tree service for LEGAL_GRADE integrity profile."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from app.application.dtos.event import EventResult


@dataclass(frozen=True)
class MerkleProofStep:
    """Single step in a Merkle proof path."""

    sibling_hash: str
    is_left_sibling: bool


class MerkleService:
    """Builds and stores Merkle trees per epoch and generates proofs."""

    def __init__(self, event_repo, merkle_repo) -> None:
        # Interfaces are kept informal here to avoid circular imports.
        self._event_repo = event_repo
        self._merkle_repo = merkle_repo

    async def build_and_store(self, tenant_id: str, epoch) -> str:
        """Build Merkle tree for all events in epoch and persist nodes.

        Args:
            tenant_id: Tenant id for the events.
            epoch: IntegrityEpoch ORM instance with id and tenant_id.

        Returns:
            Root hash of the Merkle tree.
        """
        events: list[EventResult] = await self._event_repo.get_events_for_epoch(
            tenant_id=tenant_id,
            epoch_id=epoch.id,
        )
        if not events:
            # Degenerate tree: use terminal_hash/genesis_hash as root.
            return epoch.terminal_hash or epoch.genesis_hash

        # Use merkle_leaf_hash when present; fall back to event hash.
        leaves: list[Tuple[int, str]] = []
        for ev in events:
            if ev.event_seq is None:
                continue
            leaf_hash = ev.merkle_leaf_hash or ev.hash
            leaves.append((ev.event_seq, leaf_hash))

        if not leaves:
            return epoch.terminal_hash or epoch.genesis_hash

        # Sort leaves by event_seq for deterministic tree.
        leaves.sort(key=lambda p: p[0])

        # Clear any existing nodes for idempotency.
        await self._merkle_repo.delete_for_epoch(epoch.id)

        # Build tree bottom-up.
        nodes_by_depth: list[list[Tuple[int, str]]] = []
        current_level = [(idx, h) for idx, (_, h) in enumerate(leaves)]
        nodes_by_depth.append(current_level)

        while len(current_level) > 1:
            next_level: list[Tuple[int, str]] = []
            for i in range(0, len(current_level), 2):
                left_pos, left_hash = current_level[i]
                if i + 1 < len(current_level):
                    right_pos, right_hash = current_level[i + 1]
                else:
                    right_pos, right_hash = left_pos, left_hash
                combined = (left_hash + right_hash).encode("ascii")
                parent_hash = hashlib.sha256(combined).hexdigest()
                parent_pos = i // 2
                next_level.append((parent_pos, parent_hash))
            nodes_by_depth.append(next_level)
            current_level = next_level

        root_hash = nodes_by_depth[-1][0][1]

        # Persist nodes.
        # Depth 0 = root, positions as constructed above.
        depth_count = len(nodes_by_depth)
        for depth, level in enumerate(reversed(nodes_by_depth)):
            actual_depth = depth  # 0 = root
            for position, node_hash in level:
                is_root = actual_depth == 0
                event_seq = None
                left_child = None
                right_child = None
                if actual_depth == depth_count - 1:
                    # Leaf: map back to event_seq.
                    event_seq = leaves[position][0]
                # Note: we do not persist child hashes for now; can be derived if needed.
                await self._merkle_repo.create(
                    self._merkle_repo.model(
                        epoch_id=epoch.id,
                        node_hash=node_hash,
                        left_child_hash=left_child,
                        right_child_hash=right_child,
                        event_seq=event_seq,
                        depth=actual_depth,
                        position=position,
                        is_root=is_root,
                    )
                )

        return root_hash

