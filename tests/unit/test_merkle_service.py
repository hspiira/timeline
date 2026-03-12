"""Unit tests for MerkleService (build_and_store, generate_proof)."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.dtos.event import EventResult
from app.application.services.merkle_service import (
    MerkleProofStep,
    MerkleService,
)


def _event_result(
    event_seq: int,
    event_hash: str,
    merkle_leaf_hash: str | None = None,
) -> EventResult:
    from datetime import datetime, timezone

    return EventResult(
        id="ev1",
        tenant_id="t1",
        subject_id="sub1",
        event_type="created",
        schema_version=1,
        event_time=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        payload={"name": "test"},
        previous_hash=None,
        hash=event_hash,
        workflow_instance_id=None,
        correlation_id=None,
        external_id=None,
        source=None,
        event_seq=event_seq,
        merkle_leaf_hash=merkle_leaf_hash,
    )


class _FakeMerkleRepo:
    """In-memory Merkle node store for testing."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, int, int], SimpleNamespace] = {}
        self._leaf_by_seq: dict[tuple[str, int], SimpleNamespace] = {}

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
    ) -> object:
        node = SimpleNamespace(
            epoch_id=epoch_id,
            node_hash=node_hash,
            depth=depth,
            position=position,
            is_root=is_root,
            left_child_hash=left_child_hash,
            right_child_hash=right_child_hash,
            event_seq=event_seq,
        )
        self._by_key[(epoch_id, depth, position)] = node
        if event_seq is not None:
            self._leaf_by_seq[(epoch_id, event_seq)] = node
        return node

    async def delete_for_epoch(self, epoch_id: str) -> None:
        to_del = [k for k in self._by_key if k[0] == epoch_id]
        for k in to_del:
            node = self._by_key.pop(k)
            if node.event_seq is not None:
                self._leaf_by_seq.pop((epoch_id, node.event_seq), None)

    async def get_leaf_by_event_seq(
        self, epoch_id: str, event_seq: int
    ) -> SimpleNamespace | None:
        return self._leaf_by_seq.get((epoch_id, event_seq))

    async def get_node(
        self, epoch_id: str, depth: int, position: int
    ) -> SimpleNamespace | None:
        return self._by_key.get((epoch_id, depth, position))

    def remove_node_for_testing(
        self, epoch_id: str, depth: int, position: int
    ) -> None:
        """Remove a node so tests can simulate missing/corrupt tree (e.g. missing parent)."""
        key = (epoch_id, depth, position)
        node = self._by_key.pop(key, None)
        if node is not None and node.event_seq is not None:
            self._leaf_by_seq.pop((epoch_id, node.event_seq), None)


def _recompute_root(leaf_hash: str, steps: list[MerkleProofStep]) -> str:
    """Recompute root from leaf hash and proof steps (same order as service)."""
    current = leaf_hash
    for step in steps:
        left = step.sibling_hash if step.is_left_sibling else current
        right = current if step.is_left_sibling else step.sibling_hash
        combined = (left + right).encode("ascii")
        current = hashlib.sha256(combined).hexdigest()
    return current


@pytest.fixture
def merkle_repo() -> _FakeMerkleRepo:
    return _FakeMerkleRepo()


@pytest.fixture
def merkle_service(merkle_repo: _FakeMerkleRepo) -> MerkleService:
    event_repo = AsyncMock()
    return MerkleService(event_repo=event_repo, merkle_repo=merkle_repo)


class TestMerkleServiceGenerateProof:
    """generate_proof returns path from leaf to root."""

    @pytest.mark.asyncio
    async def test_no_leaf_returns_empty(
        self, merkle_service: MerkleService, merkle_repo: _FakeMerkleRepo
    ) -> None:
        path = await merkle_service.generate_proof("epoch1", 1)
        assert path == []

    @pytest.mark.asyncio
    async def test_proof_recomputes_to_root(
        self, merkle_service: MerkleService, merkle_repo: _FakeMerkleRepo
    ) -> None:
        """After build_and_store, generate_proof path recomputes to stored root."""
        epoch_id = "ep1"
        epoch = SimpleNamespace(id=epoch_id, terminal_hash=None, genesis_hash="g" * 64)
        event_repo = merkle_service._event_repo
        event_repo.get_events_for_epoch = AsyncMock(
            return_value=[
                _event_result(1, "a" * 64),
                _event_result(2, "b" * 64),
            ]
        )

        root = await merkle_service.build_and_store("t1", epoch)
        assert root is not None
        assert len(root) == 64

        for event_seq in (1, 2):
            path = await merkle_service.generate_proof(epoch_id, event_seq)
            assert len(path) == 1  # 2 leaves -> one step to root
            leaf = await merkle_repo.get_leaf_by_event_seq(epoch_id, event_seq)
            assert leaf is not None
            recomputed = _recompute_root(leaf.node_hash, path)
            assert recomputed == root

    @pytest.mark.asyncio
    async def test_four_leaves_proof_has_two_steps(
        self, merkle_service: MerkleService, merkle_repo: _FakeMerkleRepo
    ) -> None:
        """Four leaves -> depth 2 tree -> proof has 2 steps."""
        epoch_id = "ep2"
        epoch = SimpleNamespace(id=epoch_id, terminal_hash=None, genesis_hash="g" * 64)
        event_repo = merkle_service._event_repo
        event_repo.get_events_for_epoch = AsyncMock(
            return_value=[
                _event_result(1, "a" * 64),
                _event_result(2, "b" * 64),
                _event_result(3, "c" * 64),
                _event_result(4, "d" * 64),
            ]
        )

        root = await merkle_service.build_and_store("t1", epoch)
        path = await merkle_service.generate_proof(epoch_id, 1)
        assert len(path) == 2
        leaf = await merkle_repo.get_leaf_by_event_seq(epoch_id, 1)
        assert leaf is not None
        assert _recompute_root(leaf.node_hash, path) == root

    @pytest.mark.asyncio
    async def test_single_leaf_returns_empty_proof(
        self, merkle_service: MerkleService, merkle_repo: _FakeMerkleRepo
    ) -> None:
        """Single-leaf epoch: leaf is root, proof is [] and recomputes to root."""
        epoch_id = "ep_single"
        epoch = SimpleNamespace(
            id=epoch_id, terminal_hash=None, genesis_hash="g" * 64
        )
        event_repo = merkle_service._event_repo
        event_repo.get_events_for_epoch = AsyncMock(
            return_value=[_event_result(1, "a" * 64)]
        )

        root = await merkle_service.build_and_store("t1", epoch)
        path = await merkle_service.generate_proof(epoch_id, 1)
        assert path == []
        leaf = await merkle_repo.get_leaf_by_event_seq(epoch_id, 1)
        assert leaf is not None
        assert leaf.node_hash == root
        assert _recompute_root(leaf.node_hash, path) == root

    @pytest.mark.asyncio
    async def test_odd_leaf_epoch_recomputes(
        self, merkle_service: MerkleService, merkle_repo: _FakeMerkleRepo
    ) -> None:
        """Three leaves: last leaf duplicated; proof path still recomputes to root."""
        epoch_id = "ep_odd"
        epoch = SimpleNamespace(
            id=epoch_id, terminal_hash=None, genesis_hash="g" * 64
        )
        event_repo = merkle_service._event_repo
        event_repo.get_events_for_epoch = AsyncMock(
            return_value=[
                _event_result(1, "a" * 64),
                _event_result(2, "b" * 64),
                _event_result(3, "c" * 64),
            ]
        )

        root = await merkle_service.build_and_store("t1", epoch)
        for event_seq in (1, 2, 3):
            path = await merkle_service.generate_proof(epoch_id, event_seq)
            leaf = await merkle_repo.get_leaf_by_event_seq(epoch_id, event_seq)
            assert leaf is not None
            assert _recompute_root(leaf.node_hash, path) == root

    @pytest.mark.asyncio
    async def test_missing_parent_raises_lookup_error(
        self, merkle_service: MerkleService, merkle_repo: _FakeMerkleRepo
    ) -> None:
        """When a parent node is missing mid-traversal, generate_proof raises LookupError."""
        epoch_id = "ep_corrupt"
        epoch = SimpleNamespace(
            id=epoch_id, terminal_hash=None, genesis_hash="g" * 64
        )
        event_repo = merkle_service._event_repo
        event_repo.get_events_for_epoch = AsyncMock(
            return_value=[
                _event_result(1, "a" * 64),
                _event_result(2, "b" * 64),
                _event_result(3, "c" * 64),
                _event_result(4, "d" * 64),
            ]
        )

        await merkle_service.build_and_store("t1", epoch)
        # Leaf 1 is at depth=2, position=0; its parent is depth=1, position=0.
        merkle_repo.remove_node_for_testing(epoch_id, 1, 0)

        with pytest.raises(LookupError) as exc_info:
            await merkle_service.generate_proof(epoch_id, 1)
        assert "Merkle tree incomplete" in str(exc_info.value)
        assert epoch_id in str(exc_info.value)
