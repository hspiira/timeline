"""Add projection_definition and projection_state tables (Phase 5)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "w5h6o7o8k9s0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create projection_definition, projection_state and indexes."""
    op.create_table(
        "projection_definition",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Text(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("subject_type", sa.Text(), nullable=True),
        sa.Column(
            "last_event_seq",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "name", "version", name="uq_projection_definition_tenant_name_version"
        ),
    )
    op.create_index(
        "ix_projection_definition_tenant",
        "projection_definition",
        ["tenant_id", "active"],
        unique=False,
        postgresql_where=sa.text("active = true"),
    )

    op.create_table(
        "projection_state",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "projection_id",
            sa.Text(),
            sa.ForeignKey("projection_definition.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Text(),
            sa.ForeignKey("subject.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "projection_id", "subject_id", name="uq_projection_state_projection_subject"
        ),
    )
    op.create_index(
        "ix_projection_state_projection",
        "projection_state",
        ["projection_id"],
        unique=False,
    )
    op.create_index(
        "ix_projection_state_subject",
        "projection_state",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_projection_state_gin",
        "projection_state",
        ["state"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop projection tables and indexes."""
    op.drop_index("ix_projection_state_gin", table_name="projection_state")
    op.drop_index("ix_projection_state_subject", table_name="projection_state")
    op.drop_index("ix_projection_state_projection", table_name="projection_state")
    op.drop_table("projection_state")
    op.drop_index("ix_projection_definition_tenant", table_name="projection_definition")
    op.drop_table("projection_definition")
