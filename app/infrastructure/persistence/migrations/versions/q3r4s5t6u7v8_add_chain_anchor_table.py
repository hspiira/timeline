"""Add chain_anchor table for RFC 3161 trusted timestamping.

Stores TSA receipts per tenant chain tip for external verification.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q3r4s5t6u7v8"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
        sa.Column("chain_tip_hash", sa.String(), nullable=False),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chain_anchor_tenant_tip",
        "chain_anchor",
        ["tenant_id", "chain_tip_hash"],
        unique=True,
    )
    op.create_index(
        "ix_chain_anchor_tenant_status",
        "chain_anchor",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chain_anchor_tenant_status", table_name="chain_anchor")
    op.drop_index("ix_chain_anchor_tenant_tip", table_name="chain_anchor")
    op.drop_table("chain_anchor")
