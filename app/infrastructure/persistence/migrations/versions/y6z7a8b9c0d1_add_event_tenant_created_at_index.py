"""Add composite index on event (tenant_id, created_at, event_time, id).

Supports ORDER BY created_at DESC, event_time DESC, id DESC with WHERE tenant_id
to avoid expensive sorts on large event tables.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "y6z7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "x5y6z7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create composite index for tenant-scoped event list/latest queries."""
    op.create_index(
        "ix_event_tenant_created_at",
        "event",
        ["tenant_id", "created_at", "event_time", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the composite index."""
    op.drop_index(
        "ix_event_tenant_created_at",
        table_name="event",
    )
