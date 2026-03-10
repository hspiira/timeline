"""Add subject_id to chain_anchor and replace unique index with partial indexes.

Supports tenant-level anchors (subject_id NULL) and future per-subject anchors.
See docs/CHAIN_ANCHOR_GRANULARITY.md for granularity trade-offs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "w4x5y6z7a8b9"
down_revision: str | Sequence[str] | None = "q3r4s5t6u7v8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Idempotent: only run when chain_anchor was created without subject_id (old first migration)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'chain_anchor' AND column_name = 'subject_id'"
        )
    )
    if result.scalar() is not None:
        return  # subject_id already present (new first migration or re-run)
    op.add_column(
        "chain_anchor",
        sa.Column("subject_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chain_anchor_subject_id",
        "chain_anchor",
        "subject",
        ["subject_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_chain_anchor_subject_id",
        "chain_anchor",
        ["subject_id"],
        unique=False,
    )
    op.drop_index("ix_chain_anchor_tenant_tip", table_name="chain_anchor")
    op.execute(
        "CREATE UNIQUE INDEX ix_chain_anchor_tenant_tip ON chain_anchor "
        "(tenant_id, chain_tip_hash) WHERE subject_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_chain_anchor_subject_tip ON chain_anchor "
        "(tenant_id, subject_id, chain_tip_hash) WHERE subject_id IS NOT NULL"
    )


def downgrade() -> None:
    """Idempotent: only drop indexes/FK/column if they exist (mirrors upgrade no-op when subject_id already present)."""
    conn = op.get_bind()
    inspector = inspect(conn)
    if "chain_anchor" not in inspector.get_table_names():
        return
    column_names = {col["name"] for col in inspector.get_columns("chain_anchor")}
    if "subject_id" not in column_names:
        return  # Nothing to undo (upgrade was no-op or already downgraded)
    index_names = {idx["name"] for idx in inspector.get_indexes("chain_anchor")}
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("chain_anchor")}

    if "ix_chain_anchor_subject_tip" in index_names:
        op.drop_index("ix_chain_anchor_subject_tip", table_name="chain_anchor")
    if "ix_chain_anchor_tenant_tip" in index_names:
        op.drop_index("ix_chain_anchor_tenant_tip", table_name="chain_anchor")
        op.create_index(
            "ix_chain_anchor_tenant_tip",
            "chain_anchor",
            ["tenant_id", "chain_tip_hash"],
            unique=True,
        )
    if "ix_chain_anchor_subject_id" in index_names:
        op.drop_index("ix_chain_anchor_subject_id", table_name="chain_anchor")
    if "fk_chain_anchor_subject_id" in fk_names:
        op.drop_constraint(
            "fk_chain_anchor_subject_id", "chain_anchor", type_="foreignkey"
        )
    if "subject_id" in column_names:
        op.drop_column("chain_anchor", "subject_id")
