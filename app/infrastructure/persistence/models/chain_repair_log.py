"""Chain repair log ORM model.

Records chain break detections and repair workflows.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin


class ChainRepairLog(CuidMixin, Base):
    """Chain repair workflow record. Table: chain_repair_log."""

    __tablename__ = "chain_repair_log"

    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    epoch_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("integrity_epoch.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    break_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    break_at_event_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    break_reason: Mapped[str] = mapped_column(Text, nullable=False)
    repair_initiated_by: Mapped[str] = mapped_column(
        String, ForeignKey("app_user.id"), nullable=False
    )
    repair_approved_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("app_user.id"), nullable=True
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    repair_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    repair_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_epoch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("integrity_epoch.id"), nullable=True
    )
    repair_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING_APPROVAL"
    )

