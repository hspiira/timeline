"""Merkle node ORM model.

Stores Merkle tree nodes for LEGAL_GRADE epochs.
"""

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin


class MerkleNode(CuidMixin, Base):
    """Merkle node for an integrity epoch. Table: merkle_node."""

    __tablename__ = "merkle_node"

    epoch_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("integrity_epoch.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    left_child_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    right_child_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

