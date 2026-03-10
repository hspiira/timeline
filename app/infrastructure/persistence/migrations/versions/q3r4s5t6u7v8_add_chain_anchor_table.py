"""Add chain_anchor table for RFC 3161 trusted timestamping.

Stores TSA receipts per tenant or per-subject chain tip. subject_id NULL = tenant-level;
non-null = subject-level (for future use). Partial unique indexes support both.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "q3r4s5t6u7v8"
down_revision: str | Sequence[str] | None = "i9j0k1l2m3n4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chain_anchor",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.String(),
            sa.ForeignKey("subject.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("chain_tip_hash", sa.String(), nullable=False),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tsa_url", sa.String(), nullable=False),
        sa.Column("tsa_receipt", sa.LargeBinary(), nullable=True),
        sa.Column("tsa_serial", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("event_count", sa.Integer(), nullable=True),
        sa.Column("subject_tips", JSONB, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chain_anchor_subject_id",
        "chain_anchor",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_chain_anchor_tenant_status",
        "chain_anchor",
        ["tenant_id", "status"],
        unique=False,
    )
    # Tenant-level: one anchor per (tenant_id, chain_tip_hash) when subject_id IS NULL.
    op.execute(
        "CREATE UNIQUE INDEX ix_chain_anchor_tenant_tip ON chain_anchor "
        "(tenant_id, chain_tip_hash) WHERE subject_id IS NULL"
    )
    # Subject-level: one anchor per (tenant_id, subject_id, chain_tip_hash) for future use.
    op.execute(
        "CREATE UNIQUE INDEX ix_chain_anchor_subject_tip ON chain_anchor "
        "(tenant_id, subject_id, chain_tip_hash) WHERE subject_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_chain_anchor_subject_tip", table_name="chain_anchor")
    op.drop_index("ix_chain_anchor_tenant_tip", table_name="chain_anchor")
    op.drop_index("ix_chain_anchor_tenant_status", table_name="chain_anchor")
    op.drop_index("ix_chain_anchor_subject_id", table_name="chain_anchor")
    op.drop_table("chain_anchor")
