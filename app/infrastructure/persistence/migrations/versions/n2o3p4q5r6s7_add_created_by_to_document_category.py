"""add created_by to document_category

Revision ID: n2o3p4q5r6s7
Revises: m8n9o0p1q2r3
Create Date: 2026-02-18

Audit field for document category creation (align with subject_type pattern).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, Sequence[str], None] = "m8n9o0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_category",
        sa.Column("created_by", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_document_category_created_by",
        "document_category",
        ["created_by"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_document_category_created_by_app_user",
        "document_category",
        "app_user",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_document_category_created_by_app_user",
        "document_category",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_document_category_created_by",
        table_name="document_category",
    )
    op.drop_column("document_category", "created_by")
