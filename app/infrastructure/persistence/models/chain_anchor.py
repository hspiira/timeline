"""Chain anchor ORM: RFC 3161 TSA receipt per tenant or per subject chain tip.

NULL subject_id = tenant-level anchor (one tip for the whole tenant).
Non-null subject_id = subject-level anchor (for future per-subject anchoring).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

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
    anchored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tsa_url: Mapped[str] = mapped_column(String, nullable=False)
    tsa_receipt: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    tsa_serial: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, index=True, server_default="pending"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
