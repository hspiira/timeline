"""TSA (Timestamp Authority) client protocol for RFC 3161 trusted timestamping."""

from typing import Protocol


class ITsaClient(Protocol):
    """Protocol for RFC 3161 TSA client (DIP)."""

    async def timestamp(self, data_hash: bytes) -> bytes:
        """Submit data_hash (digest) to TSA. Returns raw DER TimeStampToken."""

    def verify(self, receipt: bytes, data_hash: bytes) -> bool:
        """Verify a stored receipt against the original data_hash. Returns True if valid."""
