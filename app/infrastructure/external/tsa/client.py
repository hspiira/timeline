"""RFC 3161 TSA client using rfc3161ng and shared httpx.AsyncClient."""

import hashlib
import logging
import os

import httpx
import rfc3161ng
from pyasn1.codec.der import decoder, encoder

from app.infrastructure.external.tsa.config import TsaConfig

logger = logging.getLogger(__name__)

# Canonical hash for chain tip and RFC 3161 request/verification (must match digest_for_chain_tip).
CANONICAL_HASHNAME = "sha256"


def _digest_for_tsa(chain_tip_hash: str) -> bytes:
    """Return the digest submitted to the TSA: SHA-256 of the UTF-8 encoded chain tip hash."""
    return hashlib.sha256(chain_tip_hash.encode()).digest()


def extract_serial_from_token(token_der: bytes) -> str | None:
    """Extract TSTInfo serialNumber from a DER-encoded TimeStampToken. Returns None on parse error."""
    try:
        tst, _ = decoder.decode(token_der, asn1Spec=rfc3161ng.TimeStampToken())
        serial = tst.tst_info.getComponentByPosition(3)  # serialNumber
        return str(int(serial)) if serial is not None else None
    except Exception:
        return None


class TsaClient:
    """RFC 3161 TSA client. Uses shared httpx.AsyncClient for POST; rfc3161ng for request/response ASN.1."""

    def __init__(
        self,
        config: TsaConfig,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._client = http_client
        if self._config.hashname != CANONICAL_HASHNAME:
            raise ValueError(
                f"TSA hashname must be {CANONICAL_HASHNAME!r} for chain-tip anchoring"
            )

    def digest_for_chain_tip(self, chain_tip_hash: str) -> bytes:
        """Canonical digest for anchoring: SHA-256 of UTF-8 encoded chain tip hash."""
        return _digest_for_tsa(chain_tip_hash)

    def _build_request(self, data_digest: bytes) -> bytes:
        """Build DER-encoded TimeStampReq for the given digest. Uses a random nonce to prevent TSA response replay."""
        nonce = int.from_bytes(os.urandom(8), "big")
        request = rfc3161ng.make_timestamp_request(
            digest=data_digest,
            hashname=CANONICAL_HASHNAME,
            nonce=nonce,
        )
        return rfc3161ng.encode_timestamp_request(request)

    async def timestamp(self, data_hash: bytes) -> bytes:
        """Submit data_hash (digest) to TSA. Returns raw DER TimeStampToken.

        Args:
            data_hash: Digest (e.g. SHA-256) of the data to be timestamped.

        Returns:
            Raw DER-encoded TimeStampToken (to store in tsa_receipt).

        Raises:
            rfc3161ng.TimestampingError: On HTTP or TSA error.
        """
        body = self._build_request(data_hash)
        try:
            response = await self._client.post(
                self._config.url,
                content=body,
                headers={"Content-Type": "application/timestamp-query"},
                timeout=float(self._config.timeout_seconds),
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise rfc3161ng.TimestampingError("TSA request failed") from exc
        tsr = rfc3161ng.decode_timestamp_response(response.content)
        if int(tsr.status[0]) not in {0, 1}:  # granted | grantedWithMods
            raise rfc3161ng.TimestampingError(
                f"TSA returned status {tsr.status}; response content not a valid granted token"
            )
        token = tsr.time_stamp_token
        return encoder.encode(token)

    def verify(self, receipt: bytes, data_hash: bytes) -> bool:
        """Verify a stored receipt (DER TimeStampToken) against the original data_hash.

        When cert_path is set, loads the TSA root certificate and verifies the TSA signature.
        Without a certificate, only the digest match is checked (weaker; use cert_path in production).
        """
        cert: bytes | None = None
        if self._config.cert_path:
            with open(self._config.cert_path, "rb") as f:
                cert = f.read()
        try:
            rfc3161ng.check_timestamp(
                receipt,
                digest=data_hash,
                hashname=CANONICAL_HASHNAME,
                certificate=cert,
            )
            return True
        except (ValueError, Exception):
            return False


def digest_for_chain_tip(chain_tip_hash: str) -> bytes:
    """Canonical digest for anchoring: SHA-256 of UTF-8 encoded chain tip hash. Use when calling TSA and when verifying."""
    return _digest_for_tsa(chain_tip_hash)
