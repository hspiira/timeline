"""Add event_count and subject_tips to chain_anchor for Option C (Merkle) readiness.

No logic change: columns are nullable and not populated yet. Lets future anchoring
store event count and per-subject tip hashes at anchor time without a new migration.

Idempotent: if the table already has event_count (e.g. created by q3r4s5t6u7v8 with
these columns), this upgrade is a no-op.
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
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'chain_anchor' AND column_name = 'event_count'"
        )
    )
    if result.scalar() is not None:
        return  # columns already present (e.g. from q3r4s5t6u7v8)
    op.add_column(
        "chain_anchor",
        sa.Column("event_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chain_anchor",
        sa.Column("subject_tips", JSONB, nullable=True),
    )


def downgrade() -> None:
    conn = op.get_bind()
    for col in ("subject_tips", "event_count"):
        r = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'chain_anchor' AND column_name = :name"
            ),
            {"name": col},
        )
        if r.scalar() is not None:
            op.drop_column("chain_anchor", col)
