"""TSA client configuration (URL, timeout, optional cert path)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TsaConfig:
    """Configuration for RFC 3161 TSA client."""

    url: str
    timeout_seconds: int = 10
    cert_path: str | None = None  # path to TSA root cert for verification in production
    hashname: str = "sha256"
