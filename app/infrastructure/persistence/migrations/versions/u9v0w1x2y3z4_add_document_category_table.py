"""add document_category table

Revision ID: u9v0w1x2y3z4
Revises: t7u8v9w0x1y2
Create Date: 2025-02-15

Tenant-defined document categories with optional metadata_schema and default_retention_days.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u9v0w1x2y3z4"
down_revision: Union[str, Sequence[str], None] = "r5s6t7u8v9w0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_category",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("category_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_schema", sa.JSON(), nullable=True),
        sa.Column("default_retention_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tenant_id", "category_name", name="uq_document_category_tenant_name"
        ),
    )
    op.create_index(
        "ix_document_category_tenant_id",
        "document_category",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_category_tenant_active",
        "document_category",
        ["tenant_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_category_tenant_active", table_name="document_category")
    op.drop_index("ix_document_category_tenant_id", table_name="document_category")
    op.drop_table("document_category")
