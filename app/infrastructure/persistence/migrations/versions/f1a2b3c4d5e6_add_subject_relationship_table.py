"""Add subject_relationship table.

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-02-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subject_relationship",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("source_subject_id", sa.String(), nullable=False),
        sa.Column("target_subject_id", sa.String(), nullable=False),
        sa.Column("relationship_kind", sa.String(length=100), nullable=False),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_subject_id"], ["subject.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_subject_id"], ["subject.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "source_subject_id",
            "target_subject_id",
            "relationship_kind",
            name="uq_subject_relationship_tenant_source_target_kind",
        ),
    )
    op.create_index(
        "ix_subject_relationship_source_subject_id",
        "subject_relationship",
        ["source_subject_id"],
    )
    op.create_index(
        "ix_subject_relationship_target_subject_id",
        "subject_relationship",
        ["target_subject_id"],
    )
    op.create_index(
        "ix_subject_relationship_relationship_kind",
        "subject_relationship",
        ["relationship_kind"],
    )
    op.create_index(
        "ix_subject_relationship_source_kind",
        "subject_relationship",
        ["source_subject_id", "relationship_kind"],
    )
    op.create_index(
        "ix_subject_relationship_target_kind",
        "subject_relationship",
        ["target_subject_id", "relationship_kind"],
    )
    op.create_index(
        "ix_subject_relationship_tenant_id",
        "subject_relationship",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_table("subject_relationship")
