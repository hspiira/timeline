"""Add external_id (idempotency key) and source to event table.

Platform prerequisite for connectors: Database Change Capture (CDC), Kafka, and log parsers retry on
failure. Without a unique external key per event, retries can insert
duplicates into an immutable chain with no recovery path.

- external_id: set by connectors; optional for API callers. Unique per
  (subject_id, external_id) when not null.
- source: identifier of originating system (e.g. "api:crm", "cdc:postgres:policies").
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p2e3x4t5e6r7"
down_revision: str | Sequence[str] | None = "z7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add external_id and source columns; create idempotency and source indexes."""
    op.add_column("event", sa.Column("external_id", sa.Text(), nullable=True))
    op.add_column("event", sa.Column("source", sa.Text(), nullable=True))

    # Idempotency guard: one event per (subject, external key)
    op.create_index(
        "ix_event_subject_external_id",
        "event",
        ["subject_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    # Filtering by source system (connector queries)
    op.create_index(
        "ix_event_tenant_source",
        "event",
        ["tenant_id", "source"],
        unique=False,
        postgresql_where=sa.text("source IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop indexes and columns."""
    op.drop_index("ix_event_tenant_source", table_name="event")
    op.drop_index("ix_event_subject_external_id", table_name="event")
    op.drop_column("event", "source")
    op.drop_column("event", "external_id")
