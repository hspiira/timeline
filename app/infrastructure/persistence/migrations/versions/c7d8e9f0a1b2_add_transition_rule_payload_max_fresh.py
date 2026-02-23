"""add prior_event_payload_conditions, max_occurrences_per_stream, fresh_prior_event_type to event_transition_rule

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-02-16

Backend workflow gaps: payload-based preconditions, max occurrences per stream,
fresh prior event type (resubmission). All nullable for backward compatibility.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_transition_rule",
        sa.Column("prior_event_payload_conditions", JSONB, nullable=True),
    )
    op.add_column(
        "event_transition_rule",
        sa.Column("max_occurrences_per_stream", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_transition_rule",
        sa.Column("fresh_prior_event_type", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_transition_rule", "fresh_prior_event_type")
    op.drop_column("event_transition_rule", "max_occurrences_per_stream")
    op.drop_column("event_transition_rule", "prior_event_payload_conditions")
