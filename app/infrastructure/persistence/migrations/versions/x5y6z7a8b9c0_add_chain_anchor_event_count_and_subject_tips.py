"""Add event_count and subject_tips to chain_anchor for Option C (Merkle) readiness.

No logic change: columns are nullable and not populated yet. Lets future anchoring
store event count and per-subject tip hashes at anchor time without a new migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "x5y6z7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "w4x5y6z7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chain_anchor",
        sa.Column("event_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chain_anchor",
        sa.Column("subject_tips", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chain_anchor", "subject_tips")
    op.drop_column("chain_anchor", "event_count")
