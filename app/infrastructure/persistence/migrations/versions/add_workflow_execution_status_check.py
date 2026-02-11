"""add workflow_execution status check constraint

Revision ID: a0b1c2d3e4f5
Revises: c3d4e5f6a7b8
Create Date: 2025-02-10

Adds DB-level CheckConstraint on workflow_execution.status so only
pending, running, completed, failed are allowed (aligned with WorkflowExecutionStatus).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workflow_execution_status_check constraint."""
    op.create_check_constraint(
        "workflow_execution_status_check",
        "workflow_execution",
        "status IN ('pending', 'running', 'completed', 'failed')",
    )


def downgrade() -> None:
    """Drop workflow_execution_status_check constraint."""
    op.drop_constraint(
        "workflow_execution_status_check",
        "workflow_execution",
        type_="check",
    )
