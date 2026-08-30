"""Subject snapshot ORM: checkpoint state for state derivation performance."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin, TenantMixin


class SubjectSnapshot(CuidMixin, TenantMixin, Base):
    """One snapshot per subject (latest checkpoint). Table: subject_snapshot."""

    __tablename__ = "subject_snapshot"

    subject_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    snapshot_at_event_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
    )
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    event_count_at_snapshot: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
