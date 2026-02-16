"""Merge migration: combine event/workflow branch and subject_snapshot/search branch.

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0, t7u8v9w0x1y2
Create Date: 2026-02-16

Single head so 'alembic upgrade head' applies all migrations.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = (
    "a5b6c7d8e9f0",
    "t7u8v9w0x1y2",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge only; no schema changes."""
    pass


def downgrade() -> None:
    """Merge only; no schema changes."""
    pass
