"""add naming_template table

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-02-18

Naming conventions per scope (flow, subject, document). Unique (tenant_id, scope_type, scope_id).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "l7m8n9o0p1q2"
down_revision: Union[str, Sequence[str], None] = "k6l7m8n9o0p1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "naming_template",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.Column("template_string", sa.String(length=500), nullable=False),
        sa.Column("placeholders", sa.JSON(), nullable=True),
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
            "tenant_id",
            "scope_type",
            "scope_id",
            name="uq_naming_template_tenant_scope",
        ),
    )
    op.create_index(
        "ix_naming_template_tenant_id", "naming_template", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_naming_template_scope_type", "naming_template", ["scope_type"], unique=False
    )
    op.create_index(
        "ix_naming_template_scope_id", "naming_template", ["scope_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_naming_template_scope_id", table_name="naming_template")
    op.drop_index("ix_naming_template_scope_type", table_name="naming_template")
    op.drop_index("ix_naming_template_tenant_id", table_name="naming_template")
    op.drop_table("naming_template")
