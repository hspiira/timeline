"""add_workflow_tables

Revision ID: e469986dce88
Revises: 9e1aedfa0671
Create Date: 2025-12-17 03:50:28.515568

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e469986dce88"
down_revision: Union[str, Sequence[str], None] = "9e1aedfa0671"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create workflow tables
    op.create_table(
        "workflow",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trigger_event_type", sa.String(), nullable=False),
        sa.Column("trigger_conditions", sa.JSON(), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("max_executions_per_day", sa.Integer(), nullable=True),
        sa.Column("execution_order", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_tenant_id", "workflow", ["tenant_id"])
    op.create_index(
        "ix_workflow_trigger_event_type", "workflow", ["trigger_event_type"]
    )

    op.create_table(
        "workflow_execution",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("triggered_by_event_id", sa.String(), nullable=True),
        sa.Column("triggered_by_subject_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actions_executed", sa.Integer(), nullable=False),
        sa.Column("actions_failed", sa.Integer(), nullable=False),
        sa.Column("execution_log", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["triggered_by_event_id"], ["event.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_subject_id"], ["subject.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_execution_tenant_id", "workflow_execution", ["tenant_id"]
    )
    op.create_index(
        "ix_workflow_execution_workflow_id", "workflow_execution", ["workflow_id"]
    )
    op.create_index(
        "ix_workflow_execution_triggered_by_event_id",
        "workflow_execution",
        ["triggered_by_event_id"],
    )
    op.create_index(
        "ix_workflow_execution_triggered_by_subject_id",
        "workflow_execution",
        ["triggered_by_subject_id"],
    )
    op.create_index(
        "ix_workflow_execution_created_at", "workflow_execution", ["created_at"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop workflow tables
    op.drop_index("ix_workflow_execution_created_at", table_name="workflow_execution")
    op.drop_index(
        "ix_workflow_execution_triggered_by_subject_id", table_name="workflow_execution"
    )
    op.drop_index(
        "ix_workflow_execution_triggered_by_event_id", table_name="workflow_execution"
    )
    op.drop_index("ix_workflow_execution_workflow_id", table_name="workflow_execution")
    op.drop_index("ix_workflow_execution_tenant_id", table_name="workflow_execution")
    op.drop_table("workflow_execution")

    op.drop_index("ix_workflow_trigger_event_type", table_name="workflow")
    op.drop_index("ix_workflow_tenant_id", table_name="workflow")
    op.drop_table("workflow")
