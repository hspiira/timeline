"""Add webhook_subscription table for event push (Phase 4)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, TEXT

revision: str = "w5h6o7o8k9s0"
down_revision: str | Sequence[str] | None = "q3c4o5n6n7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create webhook_subscription table and index."""
    op.create_table(
        "webhook_subscription",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("event_types", ARRAY(TEXT), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("subject_types", ARRAY(TEXT), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_webhook_subscription_tenant",
        "webhook_subscription",
        ["tenant_id"],
        unique=False,
        postgresql_where=sa.text("active = true"),
    )


def downgrade() -> None:
    """Drop webhook_subscription table."""
    op.drop_index("ix_webhook_subscription_tenant", table_name="webhook_subscription")
    op.drop_table("webhook_subscription")
