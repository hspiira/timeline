"""Add event chain integrity partial unique indexes (ISSUE-002).

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-03-11

Prevents chain forks: one genesis per subject, one child per (subject, previous_hash).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create partial unique indexes for event chain integrity."""
    # Only one genesis event per subject (previous_hash IS NULL).
    op.create_index(
        "ix_event_subject_genesis",
        "event",
        ["subject_id"],
        unique=True,
        postgresql_where=sa.text("previous_hash IS NULL"),
    )
    # No two events may share the same parent within a subject.
    op.create_index(
        "ix_event_subject_prev_hash",
        "event",
        ["subject_id", "previous_hash"],
        unique=True,
        postgresql_where=sa.text("previous_hash IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop event chain integrity indexes."""
    op.drop_index("ix_event_subject_prev_hash", table_name="event")
    op.drop_index("ix_event_subject_genesis", table_name="event")
