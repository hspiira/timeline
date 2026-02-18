"""add document_requirement table

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-02-18

Required document categories per workflow (and optionally per step). step_definition_id null = flow-level.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "m8n9o0p1q2r3"
down_revision: Union[str, Sequence[str], None] = "l7m8n9o0p1q2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_requirement",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("step_definition_id", sa.String(), nullable=True),
        sa.Column("document_category_id", sa.String(), nullable=False),
        sa.Column("min_count", sa.Integer(), nullable=False, server_default="1"),
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
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["workflow.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_category_id"],
            ["document_category.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "workflow_id",
            "step_definition_id",
            "document_category_id",
            name="uq_document_requirement_workflow_step_category",
        ),
    )
    op.create_index(
        "ix_document_requirement_tenant_id",
        "document_requirement",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_requirement_workflow_id",
        "document_requirement",
        ["workflow_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_requirement_document_category_id",
        "document_requirement",
        ["document_category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_requirement_document_category_id",
        table_name="document_requirement",
    )
    op.drop_index(
        "ix_document_requirement_workflow_id",
        table_name="document_requirement",
    )
    op.drop_index(
        "ix_document_requirement_tenant_id",
        table_name="document_requirement",
    )
    op.drop_table("document_requirement")
