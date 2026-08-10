"""Make integrity_epoch.first_event_seq nullable.

Revision ID: b9c0d1e2f3g4
Revises: a8b9c0d1e2f3
Create Date: 2026-03-12

Epochs are created before any events; first_event_seq is set when the first
event is written. NOT NULL caused constraint violations on create_epoch.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3g4"
down_revision: str | Sequence[str] | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "integrity_epoch",
        "first_event_seq",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "integrity_epoch",
        "first_event_seq",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
