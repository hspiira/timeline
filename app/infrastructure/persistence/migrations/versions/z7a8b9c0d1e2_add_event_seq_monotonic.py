"""Add event_seq monotonic column for reliable insertion order.

created_at is transaction-scoped in PostgreSQL (same value for all rows in one
transaction). event_seq is a sequence-backed column so ORDER BY event_seq
reliably reflects insertion order for get_last_event, get_chain_tip_hash, etc.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "z7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "y6z7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add event_seq column, backfill from created_at/id order, set sequence default."""
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS event_event_seq_seq"))
    op.add_column(
        "event",
        sa.Column("event_seq", sa.BigInteger(), nullable=True),
    )
    # Backfill: assign row numbers by (created_at, id) so existing rows have order.
    op.execute(
        sa.text("""
            UPDATE event e
            SET event_seq = sub.rn
            FROM (
                SELECT id, row_number() OVER (ORDER BY created_at, id) AS rn
                FROM event
            ) sub
            WHERE e.id = sub.id
        """)
    )
    op.alter_column(
        "event",
        "event_seq",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.execute(
        sa.text(
            "SELECT setval('event_event_seq_seq', (SELECT coalesce(max(event_seq), 1) FROM event))"
        )
    )
    op.alter_column(
        "event",
        "event_seq",
        existing_type=sa.BigInteger(),
        nullable=False,
        server_default=sa.text("nextval('event_event_seq_seq'::regclass)"),
    )
    op.create_index(
        "ix_event_tenant_event_seq",
        "event",
        ["tenant_id", "event_seq"],
        unique=False,
    )


def downgrade() -> None:
    """Drop event_seq column and sequence."""
    op.drop_index("ix_event_tenant_event_seq", table_name="event")
    op.alter_column(
        "event",
        "event_seq",
        existing_type=sa.BigInteger(),
        server_default=None,
    )
    op.drop_column("event", "event_seq")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS event_event_seq_seq"))
