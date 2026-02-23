"""add subject_snapshot table for state derivation performance

Revision ID: t7u8v9w0x1y2
Revises: s6t7u8v9w0x1
Create Date: 2025-02-15

One snapshot per subject (latest checkpoint); state can be computed as
snapshot state + replay of events after snapshot_at_event_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t7u8v9w0x1y2"
down_revision: Union[str, Sequence[str], None] = "s6t7u8v9w0x1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subject_snapshot",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), sa.ForeignKey("subject.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_at_event_id", sa.String(), sa.ForeignKey("event.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("event_count_at_snapshot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subject_snapshot_subject_id",
        "subject_snapshot",
        ["subject_id"],
        unique=True,
    )
    op.create_index(
        "ix_subject_snapshot_tenant_id",
        "subject_snapshot",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_subject_snapshot_tenant_id", table_name="subject_snapshot")
    op.drop_index("ix_subject_snapshot_subject_id", table_name="subject_snapshot")
    op.drop_table("subject_snapshot")
