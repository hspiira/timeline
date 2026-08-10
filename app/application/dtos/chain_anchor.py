"""DTOs for chain anchor use cases (TSA receipt storage and retrieval)."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import ChainAnchorStatus


@dataclass(frozen=True)
class ChainAnchorResult:
    """Chain anchor read-model (result of get, list, create, update)."""

    id: str
    tenant_id: str
    subject_id: str | None  # None = tenant-level anchor; set for per-subject (future)
    chain_tip_hash: str
    anchored_at: datetime | None  # None when pending (set when confirmed)
    tsa_url: str
    tsa_receipt: bytes | None  # raw DER TimeStampToken; None when pending/failed
    tsa_serial: str | None
    status: ChainAnchorStatus
    error_message: str | None
    created_at: datetime
    # Option C readiness: event count and per-subject tips at anchor time (not populated yet).
    event_count: int | None = None
    subject_tips: dict[str, str] | None = None
