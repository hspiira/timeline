"""add document.metadata column for user-supplied document metadata

Revision ID: x2y3z4a5b6c7
Revises: w1x2y3z4a5b6
Create Date: 2026-02-15

Stores validated document category metadata (JSON) on the document record.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "x2y3z4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "w1x2y3z4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document",
        sa.Column("metadata", JSONB, nullable=True, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("document", "metadata")
