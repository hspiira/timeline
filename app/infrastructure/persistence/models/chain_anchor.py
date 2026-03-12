"""Chain anchor ORM: RFC 3161 TSA receipt per tenant or per subject chain tip.

NULL subject_id = tenant-level anchor (one tip for the whole tenant).
Non-null subject_id = subject-level anchor (for future per-subject anchoring).

event_count and subject_tips are for Option C (Merkle) readiness: record coverage
and leaf set at anchor time without changing current logic.
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SaEnum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.domain.enums import ChainAnchorStatus
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin


class ChainAnchor(CuidMixin, Base):
    """One row per (tenant_id, chain_tip_hash) for tenant-level, or (tenant_id, subject_id, chain_tip_hash) for subject-level. Table: chain_anchor."""

    __tablename__ = "chain_anchor"

    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chain_tip_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    anchored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tsa_url: Mapped[str] = mapped_column(String, nullable=False)
    tsa_receipt: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    tsa_serial: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ChainAnchorStatus] = mapped_column(
        SaEnum(ChainAnchorStatus, create_constraint=False),
        nullable=False,
        index=True,
        server_default=ChainAnchorStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Option C readiness: event count and per-subject tips at anchor time (not populated yet).
    event_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject_tips: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
