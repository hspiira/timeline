"""Extend integrity_epoch status check to include FAILED.

Revision ID: a8b9c0d1e2f3
Revises: d1e2f3a4b5c6
Create Date: 2026-03-12

Allows IntegrityEpochStatus.FAILED for epochs that could not be sealed after max retries.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | Sequence[str] | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("chk_epoch_status", "integrity_epoch", type_="check")
    op.create_check_constraint(
        "chk_epoch_status",
        "integrity_epoch",
        "status IN ('Open','Sealed','Failed','Broken','Repaired')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_epoch_status", "integrity_epoch", type_="check")
    op.create_check_constraint(
        "chk_epoch_status",
        "integrity_epoch",
        "status IN ('Open','Sealed','Broken','Repaired')",
    )
