"""Merge migration: unify heads for projections, chain integrity, and chain indexes.

Revision ID: d1e2f3a4b5c6
Revises: a7b8c9d0e1f2, c1d2e3f4g5h6, j0k1l2m3n4o5
Create Date: 2026-03-12

No schema changes; establishes a single linear head.
"""

from collections.abc import Sequence

revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = (
    "a7b8c9d0e1f2",
    "c1d2e3f4g5h6",
    "j0k1l2m3n4o5",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge only; no schema changes."""
    # This migration intentionally does nothing.
    pass


def downgrade() -> None:
    """Downgrade merge; no schema changes."""
    # There is no structural change to revert.
    pass

