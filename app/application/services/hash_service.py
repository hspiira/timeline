"""Hash service for event chain integrity (canonical JSON + algorithm)."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.shared.utils.datetime import ensure_utc


class HashAlgorithm(ABC):
    """Abstract hash algorithm (OCP)."""

    @abstractmethod
    def hash(self, data: str) -> str:
        """Compute hash of input string."""
        ...


class SHA256Algorithm(HashAlgorithm):
    """SHA-256 implementation."""

    def hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()


class SHA512Algorithm(HashAlgorithm):
    """SHA-512 implementation."""

    def hash(self, data: str) -> str:
        return hashlib.sha512(data.encode()).hexdigest()


class HashService:
    """Single source of truth for event hash computation (IHashService)."""

    def __init__(self, algorithm: HashAlgorithm | None = None) -> None:
        self.algorithm = algorithm or SHA256Algorithm()

    @staticmethod
    def canonical_json(data: dict[str, Any]) -> str:
        """Canonical JSON for deterministic hashing."""
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def compute_hash(
        self,
        subject_id: str,
        event_type: str,
        schema_version: int,
        event_time: datetime,
        payload: dict[str, Any],
        previous_hash: str | None,
    ) -> str:
        """Compute hash for event (chain integrity)."""
        event_time_utc = ensure_utc(event_time) or event_time
        hash_content = {
            "subject_id": subject_id,
            "event_type": event_type,
            "schema_version": schema_version,
            "event_time": event_time_utc.isoformat(),
            "payload": payload,
            "previous_hash": previous_hash,
        }
        return self.algorithm.hash(self.canonical_json(hash_content))
