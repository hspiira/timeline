"""Integrity epoch ORM model.

Represents a bounded segment of the hash chain per (tenant, subject).
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin


class IntegrityEpoch(CuidMixin, Base):
    """Integrity epoch for a subject under a tenant. Table: integrity_epoch."""

    __tablename__ = "integrity_epoch"

    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    epoch_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    genesis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    terminal_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_event_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_event_seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sealed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tsa_anchor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tsa_anchor.id"), nullable=True
    )
    merkle_root: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

