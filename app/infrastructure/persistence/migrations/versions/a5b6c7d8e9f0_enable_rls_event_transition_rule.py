"""enable RLS on event_transition_rule table

Revision ID: a5b6c7d8e9f0
Revises: z4a5b6c7d8e9
Create Date: 2026-02-16

Row-level security for event_transition_rule (tenant-scoped).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "z4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE event_transition_rule ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON event_transition_rule "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON event_transition_rule")
    op.execute("ALTER TABLE event_transition_rule DISABLE ROW LEVEL SECURITY")
