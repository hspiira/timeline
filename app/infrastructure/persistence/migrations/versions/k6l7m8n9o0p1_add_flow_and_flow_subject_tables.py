"""add flow and flow_subject tables

Revision ID: k6l7m8n9o0p1
Revises: b6c7d8e9f0a1
Create Date: 2026-02-18

Flow = named workflow instance grouping many subjects.
flow_subject = junction table (flow_id, subject_id, optional role).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "k6l7m8n9o0p1"
down_revision: Union[str, Sequence[str], None] = (
    "b6c7d8e9f0a1",
    "j5e6f7a8b9c0",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flow",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("hierarchy_values", sa.JSON(), nullable=True),
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
            ["workflow_id"], ["workflow.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_flow_tenant_id", "flow", ["tenant_id"], unique=False)
    op.create_index("ix_flow_name", "flow", ["name"], unique=False)
    op.create_index("ix_flow_workflow_id", "flow", ["workflow_id"], unique=False)

    op.create_table(
        "flow_subject",
        sa.Column("flow_id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("flow_id", "subject_id"),
        sa.ForeignKeyConstraint(["flow_id"], ["flow.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subject.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_flow_subject_flow_id", "flow_subject", ["flow_id"], unique=False
    )
    op.create_index(
        "ix_flow_subject_subject_id", "flow_subject", ["subject_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_flow_subject_flow_subject",
        "flow_subject",
        ["flow_id", "subject_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_flow_subject_flow_subject", "flow_subject", type_="unique"
    )
    op.drop_index("ix_flow_subject_subject_id", table_name="flow_subject")
    op.drop_index("ix_flow_subject_flow_id", table_name="flow_subject")
    op.drop_table("flow_subject")
    op.drop_index("ix_flow_workflow_id", table_name="flow")
    op.drop_index("ix_flow_name", table_name="flow")
    op.drop_index("ix_flow_tenant_id", table_name="flow")
    op.drop_table("flow")
