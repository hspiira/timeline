"""add task table for workflow create_task action

Revision ID: v0w1x2y3z4a5
Revises: u9v0w1x2y3z4
Create Date: 2026-02-15

Task record created by workflow action create_task. Assignable to role or user.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v0w1x2y3z4a5"
down_revision: Union[str, Sequence[str], None] = "u9v0w1x2y3z4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=True),
        sa.Column("assigned_to_role_id", sa.String(), nullable=True),
        sa.Column("assigned_to_user_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("description", sa.Text(), nullable=True),
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
            ["subject_id"], ["subject.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["event.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_role_id"], ["role.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"], ["app_user.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_task_tenant_id", "task", ["tenant_id"], unique=False)
    op.create_index("ix_task_subject_id", "task", ["subject_id"], unique=False)
    op.create_index("ix_task_event_id", "task", ["event_id"], unique=False)
    op.create_index(
        "ix_task_tenant_subject", "task", ["tenant_id", "subject_id"], unique=False
    )
    op.create_index(
        "ix_task_assigned",
        "task",
        ["tenant_id", "assigned_to_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_assigned", table_name="task")
    op.drop_index("ix_task_tenant_subject", table_name="task")
    op.drop_index("ix_task_event_id", table_name="task")
    op.drop_index("ix_task_subject_id", table_name="task")
    op.drop_index("ix_task_tenant_id", table_name="task")
    op.drop_table("task")
