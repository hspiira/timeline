"""TSA service: anchor payload hashes via RFC 3161 and persist to tsa_anchor table."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.infrastructure.external.tsa.client import (
    extract_gen_time_from_token,
    extract_serial_from_token,
)

if TYPE_CHECKING:
    from app.application.interfaces.tsa_client import ITsaClient
    from app.infrastructure.persistence.repositories.tsa_anchor_repo import (
        TsaAnchorRepository,
    )


class TsaService:
    """Anchors payload hashes with an RFC 3161 TSA and stores tokens in tsa_anchor."""

    def __init__(
        self,
        tsa_client: ITsaClient,
        tsa_anchor_repo: TsaAnchorRepository,
        tsa_provider_url: str,
    ) -> None:
        self._tsa_client = tsa_client
        self._repo = tsa_anchor_repo
        self._tsa_provider_url = tsa_provider_url

    async def anchor(
        self,
        tenant_id: str,
        payload_hash_hex: str,
        anchor_type: str,
    ) -> str:
        """Submit payload_hash to TSA, store token in tsa_anchor; return anchor id."""
        digest = self._tsa_client.digest_for_chain_tip(payload_hash_hex)
        token = await self._tsa_client.timestamp(digest)
        tsa_time = extract_gen_time_from_token(token) or datetime.now(timezone.utc)
        serial = extract_serial_from_token(token)
        row = await self._repo.create_anchor(
            tenant_id=tenant_id,
            anchor_type=anchor_type,
            payload_hash=payload_hash_hex,
            tsa_token=token,
            tsa_provider=self._tsa_provider_url,
            tsa_reported_time=tsa_time,
            tsa_serial=serial,
        )
        return row.id

    async def verify(self, anchor_id: str) -> bool:
        """Verify stored TSA token against payload_hash; update verification_status. Return True if valid."""
        anchor = await self._repo.get_by_id(anchor_id)
        if not anchor:
            return False
        digest = self._tsa_client.digest_for_chain_tip(anchor.payload_hash)
        ok = self._tsa_client.verify(anchor.tsa_token, digest)
        await self._repo.update_verification_status(
            anchor_id,
            "VERIFIED" if ok else "FAILED",
            verified_at=datetime.now(timezone.utc),
        )
        return ok
