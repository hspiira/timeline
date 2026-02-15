"""enable RLS for tenant isolation

Revision ID: w1x2y3z4a5b6
Revises: v0w1x2y3z4a5
Create Date: 2026-02-15

Enables row-level security on tenant-scoped tables. Policy: only rows where
tenant_id (or id for tenant table) equals current_setting('app.current_tenant_id').
The application must SET app.current_tenant_id at the start of each request (e.g. from JWT).
Migrations and admin scripts should use a DB role with BYPASSRLS; the app role must not.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "w1x2y3z4a5b6"
down_revision: Union[str, Sequence[str], None] = "v0w1x2y3z4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that have tenant_id column (policy: tenant_id = current_setting(...))
TENANT_SCOPED_TABLES = [
    "subject",
    "event",
    "document",
    "app_user",
    "role",
    "permission",
    "role_permission",
    "user_role",
    "event_schema",
    "workflow",
    "workflow_execution",
    "subject_type",
    "document_category",
    "subject_snapshot",
    "audit_log",
    "task",
    "email_account",
    "oauth_provider_config",
    "oauth_state",
    "oauth_audit_log",
]


def upgrade() -> None:
    # Tenant table: policy on id (each tenant sees only its own row)
    op.execute("ALTER TABLE tenant ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON tenant "
        "USING (id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (id = current_setting('app.current_tenant_id', true))"
    )

    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
        )


def downgrade() -> None:
    for table in reversed(TENANT_SCOPED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON tenant")
    op.execute("ALTER TABLE tenant DISABLE ROW LEVEL SECURITY")
