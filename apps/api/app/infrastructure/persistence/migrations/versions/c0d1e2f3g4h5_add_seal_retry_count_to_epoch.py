"""Add seal_retry_count to integrity_epoch for persistent retry tracking.

Revision ID: c0d1e2f3g4h5
Revises: b9c0d1e2f3g4
Create Date: 2026-03-12

Seal failures are counted on the row so retries persist across restarts;
epoch sealing job uses this to mark epochs FAILED after max retries.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c0d1e2f3g4h5"
down_revision: str | Sequence[str] | None = "b9c0d1e2f3g4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists() -> bool:
    """Return whether ``integrity_epoch.seal_retry_count`` is already present."""
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = 'integrity_epoch' "
                "AND column_name = 'seal_retry_count'"
            )
        ).scalar()
    )


def upgrade() -> None:
    """Add the ``seal_retry_count`` column to ``integrity_epoch``.

    Guarded: revision c1d2e3f4g5h6 was edited after release to include this column
    in its ``CREATE TABLE``, so any database migrated after that edit already has
    it and a bare ``add_column`` here raises DuplicateColumnError.
    """
    if _column_exists():
        return
    op.add_column(
        "integrity_epoch",
        sa.Column("seal_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop the ``seal_retry_count`` column from ``integrity_epoch`` if present."""
    if not _column_exists():
        return
    op.drop_column("integrity_epoch", "seal_retry_count")
