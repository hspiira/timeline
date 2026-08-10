"""Enable RLS on every remaining tenant-scoped table, and force it for owners.

Revision ID: d2e3f4g5h6i7
Revises: c0d1e2f3g4h5
Create Date: 2026-08-11

Extends w1x2y3z4a5b6, which covered only the 21 tables that existed in
February. Tables added since (chain anchoring, integrity epochs, Merkle nodes,
projections, webhooks, connectors, flows, naming templates, relationship kinds)
had no RLS at all.

Two kinds of policy:

* Direct: table has ``tenant_id``, so the policy compares it to
  ``current_setting('app.current_tenant_id')`` — same shape as w1x2y3z4a5b6.
* Indirect: table has no ``tenant_id``, so the policy tests an ``EXISTS`` against
  its parent's ``tenant_id``. The parent's own policy also applies, so the row is
  filtered consistently.

``alembic_version`` is deliberately excluded: it holds no tenant data and RLS on
it would risk breaking Alembic itself.

FORCE ROW LEVEL SECURITY is then applied to every table in ``public`` that has RLS
enabled, discovered from the catalogue rather than a hardcoded list. Without FORCE
a table's owner silently bypasses its own policies. Note this changes nothing for a
role holding the BYPASSRLS attribute — that bypass is independent of ownership, and
the application role must not have it (see w1x2y3z4a5b6's note on role separation).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d2e3f4g5h6i7"
down_revision: str | Sequence[str] | None = "c0d1e2f3g4h5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_SETTING = "current_setting('app.current_tenant_id', true)"

# Tables gaining RLS here that carry tenant_id directly.
NEW_DIRECT_TABLES = [
    "chain_anchor",
    "chain_repair_log",
    "connector_mapping",
    "document_requirement",
    "flow",
    "integrity_epoch",
    "naming_template",
    "projection_definition",
    "relationship_kind",
    "subject_relationship",
    "tenant_integrity_profile_history",
    "tsa_anchor",
    "webhook_subscription",
]

# Tables with no tenant_id: (table, fk_column, parent_table, parent_key).
NEW_INDIRECT_TABLES = [
    ("flow_subject", "flow_id", "flow", "id"),
    ("merkle_node", "epoch_id", "integrity_epoch", "id"),
    ("projection_state", "projection_id", "projection_definition", "id"),
    ("password_set_token", "user_id", "app_user", "id"),
]

_SET_FORCE_ON_ALL_RLS_TABLES = """
DO $$
DECLARE t regclass;
BEGIN
  FOR t IN
    SELECT c.oid::regclass
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE %s %s ROW LEVEL SECURITY', t, '{force}');
  END LOOP;
END $$;
"""


def upgrade() -> None:
    """Enable RLS and tenant_isolation policies on remaining tables; force RLS on all."""
    for table in NEW_DIRECT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = {_TENANT_SETTING}) "
            f"WITH CHECK (tenant_id = {_TENANT_SETTING})"
        )

    for table, fk, parent, parent_key in NEW_INDIRECT_TABLES:
        predicate = (
            f"EXISTS (SELECT 1 FROM {parent} p "
            f"WHERE p.{parent_key} = {table}.{fk} "
            f"AND p.tenant_id = {_TENANT_SETTING})"
        )
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        )

    # Derived from the schema rather than a hardcoded list, so no RLS-enabled
    # table can be missed (w1x2y3z4a5b6's list already omitted
    # event_transition_rule, which picked up RLS from a later migration).
    op.execute(_SET_FORCE_ON_ALL_RLS_TABLES.format(force="FORCE"))


def downgrade() -> None:
    """Drop the policies added here and lift FORCE from all tenant-scoped tables."""
    op.execute(_SET_FORCE_ON_ALL_RLS_TABLES.format(force="NO FORCE"))

    for table, _, _, _ in reversed(NEW_INDIRECT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in reversed(NEW_DIRECT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
