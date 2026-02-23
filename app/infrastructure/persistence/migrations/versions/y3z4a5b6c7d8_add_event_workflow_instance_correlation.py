"""add event workflow_instance_id and correlation_id for event linking

Revision ID: y3z4a5b6c7d8
Revises: x2y3z4a5b6c7
Create Date: 2026-02-16

Optional fields to group events by process run (stream); chain remains per subject.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "y3z4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "x2y3z4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event",
        sa.Column("workflow_instance_id", sa.String(), nullable=True),
    )
    op.add_column(
        "event",
        sa.Column("correlation_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_event_workflow_instance_id",
        "event",
        ["workflow_instance_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_correlation_id",
        "event",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_tenant_subject_workflow",
        "event",
        ["tenant_id", "subject_id", "workflow_instance_id"],
        unique=False,
        postgresql_where=sa.text("workflow_instance_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_tenant_subject_workflow",
        table_name="event",
        postgresql_where=sa.text("workflow_instance_id IS NOT NULL"),
    )
    op.drop_index("ix_event_correlation_id", table_name="event")
    op.drop_index("ix_event_workflow_instance_id", table_name="event")
    op.drop_column("event", "correlation_id")
    op.drop_column("event", "workflow_instance_id")
