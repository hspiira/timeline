"""Add allowed_event_types to subject_type.

Revision ID: e0f1a2b3c4d5
Revises: e9f0a1b2c3d4
Create Date: 2026-02-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "e0f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "e9f0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subject_type",
        sa.Column("allowed_event_types", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subject_type", "allowed_event_types")
