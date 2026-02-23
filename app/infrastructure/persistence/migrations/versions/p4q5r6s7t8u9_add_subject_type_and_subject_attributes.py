"""add subject_type table and subject display_name/attributes

Revision ID: p4q5r6s7t8u9
Revises: n1o2p3q4r5s6
Create Date: 2025-02-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p4q5r6s7t8u9"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5s6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Subject type configuration (tenant-defined subject types with optional schema)
    op.create_table(
        "subject_type",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("type_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column("has_timeline", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_documents", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "type_name", name="uq_subject_type_tenant_type"),
    )
    op.create_index(
        "ix_subject_type_tenant_id", "subject_type", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_subject_type_tenant_active",
        "subject_type",
        ["tenant_id", "is_active"],
        unique=False,
    )

    # Add display_name and attributes to subject (nullable for backfill later)
    op.add_column(
        "subject",
        sa.Column("display_name", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "subject",
        sa.Column("attributes", sa.JSON(), nullable=True, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("subject", "attributes")
    op.drop_column("subject", "display_name")

    op.drop_index("ix_subject_type_tenant_active", table_name="subject_type")
    op.drop_index("ix_subject_type_tenant_id", table_name="subject_type")
    op.drop_table("subject_type")
