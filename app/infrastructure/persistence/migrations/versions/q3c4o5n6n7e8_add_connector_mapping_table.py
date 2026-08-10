"""Add connector_mapping table for DB-backed source→event mappings.

Stores per-tenant, per-connector mapping config (column_mappings,
event_type_rules) for CDC/Kafka. Used by connector framework to resolve
event_type from source rows.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "q3c4o5n6n7e8"
down_revision: str | Sequence[str] | None = "p2e3x4t5e6r7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create connector_mapping table and index."""
    op.create_table(
        "connector_mapping",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connector_type", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column(
            "column_mappings",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "event_type_rules",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("default_schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "connector_type", "source_name", name="uq_connector_mapping_tenant_type_source"),
    )
    op.create_index(
        "ix_connector_mapping_tenant_type",
        "connector_mapping",
        ["tenant_id", "connector_type"],
        unique=False,
        postgresql_where=sa.text("active = true"),
    )


def downgrade() -> None:
    """Drop connector_mapping table."""
    op.drop_index("ix_connector_mapping_tenant_type", table_name="connector_mapping")
    op.drop_table("connector_mapping")
