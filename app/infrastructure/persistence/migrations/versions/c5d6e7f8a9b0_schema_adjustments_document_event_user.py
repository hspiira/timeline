"""Schema adjustments: document, event, event_schema, user, user_role.

Split from e469986dce88 so workflow table creation and these adjustments
can be reviewed and rolled back independently.
Revision ID: c5d6e7f8a9b0
Revises: e469986dce88
Create Date: (manual split)

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "e469986dce88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema adjustments (document, event, event_schema, user, user_role)."""
    op.alter_column(
        "document",
        "file_size",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "document", "is_latest_version", existing_type=sa.BOOLEAN(), nullable=False
    )
    op.drop_index(op.f("ix_document_tenant_checksum"), table_name="document")
    op.create_index(
        "ix_document_checksum_unique",
        "document",
        ["tenant_id", "checksum"],
        unique=True,
    )
    op.create_index(
        "ix_document_tenant_subject",
        "document",
        ["tenant_id", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ux_document_versions",
        "document",
        ["tenant_id", "subject_id", "parent_document_id", "version"],
        unique=True,
    )
    op.drop_constraint(op.f("event_hash_key"), "event", type_="unique")
    op.drop_index(op.f("ix_event_schema_active"), table_name="event_schema")
    op.execute("ALTER TABLE app_user ALTER COLUMN is_active DROP DEFAULT")
    op.execute(
        "ALTER TABLE app_user ALTER COLUMN is_active TYPE BOOLEAN USING is_active::boolean"
    )
    op.execute("ALTER TABLE app_user ALTER COLUMN is_active SET DEFAULT true")
    op.alter_column(
        "user_role",
        "assigned_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("user_role_assigned_by_fkey"), "user_role", type_="foreignkey"
    )
    op.create_foreign_key(None, "user_role", "app_user", ["assigned_by"], ["id"])


def downgrade() -> None:
    """Revert schema adjustments."""
    op.drop_constraint(None, "user_role", type_="foreignkey")
    op.create_foreign_key(
        op.f("user_role_assigned_by_fkey"),
        "user_role",
        "app_user",
        ["assigned_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column(
        "user_role",
        "assigned_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "app_user",
        "is_active",
        existing_type=sa.Boolean(),
        type_=sa.VARCHAR(),
        existing_nullable=False,
        existing_server_default=sa.text("'true'::character varying"),
    )
    op.create_index(
        op.f("ix_event_schema_active"),
        "event_schema",
        ["tenant_id", "event_type", "is_active"],
        unique=False,
    )
    op.create_unique_constraint(op.f("event_hash_key"), "event", ["hash"])
    op.drop_index("ux_document_versions", table_name="document")
    op.drop_index("ix_document_tenant_subject", table_name="document")
    op.drop_index("ix_document_checksum_unique", table_name="document")
    op.create_index(
        op.f("ix_document_tenant_checksum"),
        "document",
        ["tenant_id", "checksum"],
        unique=False,
    )
    op.alter_column(
        "document", "is_latest_version", existing_type=sa.BOOLEAN(), nullable=True
    )
    op.alter_column(
        "document",
        "file_size",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
