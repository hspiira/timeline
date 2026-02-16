"""add event_transition_rule table for transition validation

Revision ID: z4a5b6c7d8e9
Revises: y3z4a5b6c7d8
Create Date: 2026-02-16

Stores rules: event_type requires required_prior_event_types (JSONB array) in stream.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "z4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "y3z4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_transition_rule",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("required_prior_event_types", JSONB, nullable=False),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_transition_rule_tenant_id",
        "event_transition_rule",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_transition_rule_event_type",
        "event_transition_rule",
        ["event_type"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_event_transition_rule_tenant_event_type",
        "event_transition_rule",
        ["tenant_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_event_transition_rule_tenant_event_type",
        "event_transition_rule",
        type_="unique",
    )
    op.drop_index("ix_event_transition_rule_event_type", table_name="event_transition_rule")
    op.drop_index("ix_event_transition_rule_tenant_id", table_name="event_transition_rule")
    op.drop_table("event_transition_rule")
