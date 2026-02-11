"""Add composite indexes for email_account and workflow_execution

Revision ID: h0i1j2k3l4m5
Revises: d7e8f9a0b1c2, g8h9i0j1k2l3
Create Date: 2025-02-11

Adds composite indexes to match repository query patterns:
- email_account (tenant_id, subject_id): list/get by tenant and subject
- workflow_execution (tenant_id, workflow_id): list executions by workflow
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "h0i1j2k3l4m5"
down_revision: Union[str, Sequence[str], None] = (
    "d7e8f9a0b1c2",
    "g8h9i0j1k2l3",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_email_account_tenant_subject",
        "email_account",
        ["tenant_id", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_workflow_execution_tenant_workflow",
        "workflow_execution",
        ["tenant_id", "workflow_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_execution_tenant_workflow",
        table_name="workflow_execution",
    )
    op.drop_index(
        "ix_email_account_tenant_subject",
        table_name="email_account",
    )
