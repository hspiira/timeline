"""TSA anchor ORM model.

Stores RFC 3161 TimeStampTokens returned by the external TSA provider.
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum as SaEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import TsaAnchorType, TsaVerificationStatus
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin


class TsaAnchor(CuidMixin, Base):
    """Time-stamp authority anchor for payload hashes. Table: tsa_anchor."""

    __tablename__ = "tsa_anchor"

    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anchor_type: Mapped[TsaAnchorType] = mapped_column(
        SaEnum(
            TsaAnchorType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tsa_token: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    tsa_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    tsa_serial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    anchored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tsa_reported_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_status: Mapped[TsaVerificationStatus] = mapped_column(
        SaEnum(
            TsaVerificationStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
        default=TsaVerificationStatus.PENDING,
    )

