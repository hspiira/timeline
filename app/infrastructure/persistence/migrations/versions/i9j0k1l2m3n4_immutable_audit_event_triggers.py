"""Add triggers to enforce immutability of event and audit_log tables.

Revision ID: i9j0k1l2m3n4
Revises: n2o3p4q5r6s7
Create Date: 2026-02-23

Event and audit_log are append-only for regulatory compliance. These triggers
prevent UPDATE and DELETE at the database level (in addition to ORM/repo guards).
Migrations and admin scripts that must modify these tables should use a role
with BYPASSRLS; the application role must not bypass RLS.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "n2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _trigger_function_event() -> str:
    """Return SQL for trigger function that blocks event UPDATE/DELETE."""
    return """
    CREATE OR REPLACE FUNCTION prevent_event_mutation()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION 'event rows are immutable; create a compensating event instead'
            USING ERRCODE = 'integrity_constraint_violation';
    END;
    $$
    """


def _trigger_function_audit_log() -> str:
    """Return SQL for trigger function that blocks audit_log UPDATE/DELETE."""
    return """
    CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION 'audit_log rows are append-only and cannot be updated or deleted'
            USING ERRCODE = 'integrity_constraint_violation';
    END;
    $$
    """


def upgrade() -> None:
    # Event: BEFORE UPDATE OR DELETE raise
    op.execute(_trigger_function_event())
    op.execute(
        "CREATE TRIGGER prevent_event_update_delete "
        "BEFORE UPDATE OR DELETE ON event "
        "FOR EACH ROW EXECUTE PROCEDURE prevent_event_mutation()"
    )
    # audit_log: BEFORE UPDATE OR DELETE raise
    op.execute(_trigger_function_audit_log())
    op.execute(
        "CREATE TRIGGER prevent_audit_log_update_delete "
        "BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE PROCEDURE prevent_audit_log_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update_delete ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")
    op.execute("DROP TRIGGER IF EXISTS prevent_event_update_delete ON event")
    op.execute("DROP FUNCTION IF EXISTS prevent_event_mutation()")
