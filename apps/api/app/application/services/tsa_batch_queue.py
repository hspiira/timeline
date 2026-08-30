"""In-memory queue for TSA batch anchoring (COMPLIANCE profile).

The queue lives in application layer so both EventService and background
workers can use it without introducing infrastructure dependencies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TsaBatchItem:
    """Single event to include in a TSA batch anchor."""

    tenant_id: str
    event_id: str
    payload_hash_hex: str


class TsaBatchQueue:
    """Process-local, in-memory queue for TSA batch items.

    Not durable; intended for COMPLIANCE profile where occasional loss is acceptable.
    """

    def __init__(self) -> None:
        self._items: list[TsaBatchItem] = []
        self._lock = asyncio.Lock()

    async def enqueue(self, item: TsaBatchItem) -> None:
        """Append one item to the queue."""
        async with self._lock:
            self._items.append(item)

    async def drain(self, max_items: int) -> list[TsaBatchItem]:
        """Pop up to max_items items from the queue (FIFO order)."""
        async with self._lock:
            if not self._items:
                return []
            batch = self._items[:max_items]
            self._items = self._items[max_items:]
            return batch


# Default singleton used by EventService and TSA batch worker.
DEFAULT_TSA_BATCH_QUEUE = TsaBatchQueue()

