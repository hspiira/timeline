"""Anchor chain tips use case: submit tenant chain tip hash to TSA and store receipt."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.application.dtos.chain_anchor import ChainAnchorResult
from app.shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.application.interfaces.repositories import (
        IChainAnchorRepository,
        IEventRepository,
    )
    from app.application.interfaces.tsa_client import ITsaClient

logger = logging.getLogger(__name__)

# If a pending row is younger than this, skip (another process is likely in flight).
PENDING_GRACE_SECONDS = 30


def _is_recent(anchor: ChainAnchorResult) -> bool:
    """True if anchor was created less than PENDING_GRACE_SECONDS ago."""
    now = utc_now()
    delta = (now - anchor.created_at).total_seconds()
    return 0 <= delta < PENDING_GRACE_SECONDS


class AnchorChainTipsUseCase:
    """Orchestrates fetching the tenant chain tip, idempotent pending row, TSA call, and store receipt."""

    def __init__(
        self,
        event_repo: "IEventRepository",
        anchor_repo: "IChainAnchorRepository",
        tsa_client: "ITsaClient",
        tsa_url: str,
    ) -> None:
        self._event_repo = event_repo
        self._anchor_repo = anchor_repo
        self._tsa_client = tsa_client
        self._tsa_url = tsa_url

    async def run_for_tenant(self, tenant_id: str) -> ChainAnchorResult | None:
        """Anchor the current chain tip for the tenant. Idempotent; returns existing if already confirmed.

        Returns:
            The (possibly existing) confirmed anchor result, or None if tenant has no events.
        """
        from app.infrastructure.external.tsa.client import (
            digest_for_chain_tip,
            extract_serial_from_token,
        )

        tip = await self._event_repo.get_chain_tip_hash(tenant_id)
        if tip is None:
            return None

        existing = await self._anchor_repo.get_by_tenant_and_tip(tenant_id, tip)
        if existing is not None:
            if existing.status == "confirmed":
                return existing
            if existing.status == "pending" and _is_recent(existing):
                return None  # in flight, skip
            # Stale pending or failed: reuse the row.
            await self._anchor_repo.update_to_pending(existing.id)
            anchor_id = existing.id
        else:
            anchored_at = utc_now()
            anchor = await self._anchor_repo.create_pending(
                tenant_id=tenant_id,
                chain_tip_hash=tip,
                anchored_at=anchored_at,
                tsa_url=self._tsa_url,
            )
            anchor_id = anchor.id

        try:
            data_hash = digest_for_chain_tip(tip)
            receipt = await self._tsa_client.timestamp(data_hash)
            serial = extract_serial_from_token(receipt)
            updated = await self._anchor_repo.update_confirmed(
                anchor_id, tsa_receipt=receipt, tsa_serial=serial
            )
            return updated
        except Exception as e:
            await self._anchor_repo.update_failed(anchor_id, error_message=str(e))
            logger.warning(
                "Chain anchor failed for tenant_id=%s: %s",
                tenant_id,
                e,
                exc_info=True,
            )
            raise
