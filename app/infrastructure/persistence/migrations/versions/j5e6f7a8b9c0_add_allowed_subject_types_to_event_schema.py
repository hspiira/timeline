"""Add allowed_subject_types to event_schema.

Revision ID: j5e6f7a8b9c0
Revises: i4d5e6f7a8b9
Create Date: 2026-02-18

Adds optional JSONB column allowed_subject_types to event_schema to restrict
which subject types can emit events for this schema (Option B: schema-level allowlist).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "j5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "i4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_schema",
        sa.Column("allowed_subject_types", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_schema", "allowed_subject_types")
