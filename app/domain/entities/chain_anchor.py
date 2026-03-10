"""Chain anchor domain entity.

Represents a single RFC 3161 timestamp receipt for a tenant's chain tip.
Used for external verification; no business logic beyond data shape.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChainAnchorEntity:
    """Immutable representation of a chain anchor (TSA receipt for chain tip)."""

    id: str
    tenant_id: str
    chain_tip_hash: str
    anchored_at: datetime
    tsa_url: str
    status: str  # pending | confirmed | failed
    tsa_serial: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
