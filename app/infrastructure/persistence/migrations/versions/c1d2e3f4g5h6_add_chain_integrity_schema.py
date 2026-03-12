"""Add chain integrity schema: profiles, epochs, TSA, Merkle, repair log.

Revision ID: c1d2e3f4g5h6
Revises: m8n9o0p1q2r3
Create Date: 2026-03-12

Implements integrity profiles, epochs, TSA anchors, Merkle trees, and chain repair log.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4g5h6"
down_revision: str | Sequence[str] | None = "m8n9o0p1q2r3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 3.1 tenants — additions
    op.add_column(
        "tenant",
        sa.Column(
            "integrity_profile",
            sa.String(length=20),
            nullable=False,
            server_default="STANDARD",
        ),
    )
    op.add_column(
        "tenant",
        sa.Column(
            "profile_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "tenant",
        sa.Column(
            "profile_changed_by",
            sa.String(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "chk_integrity_profile",
        "tenant",
        "integrity_profile IN ('STANDARD','COMPLIANCE','LEGAL_GRADE')",
    )
    op.execute(
        "COMMENT ON COLUMN tenant.integrity_profile IS "
        "'Active integrity profile. Changes are journalled in tenant_integrity_profile_history.'"
    )

    # 3.2 tenant_integrity_profile_history
    op.create_table(
        "tenant_integrity_profile_history",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("previous_profile", sa.String(length=20), nullable=True),
        sa.Column("new_profile", sa.String(length=20), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "changed_by_user_id",
            sa.String(),
            sa.ForeignKey("app_user.id"),
            nullable=False,
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("effective_from_seq", sa.BigInteger(), nullable=False),
        sa.Column("cooling_off_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "new_profile IN ('STANDARD','COMPLIANCE','LEGAL_GRADE')",
            name="chk_tip_new_profile",
        ),
    )
    op.create_index(
        "idx_tip_history_tenant",
        "tenant_integrity_profile_history",
        ["tenant_id", "changed_at"],
        unique=False,
    )

    # 3.5 tsa_anchors (before integrity_epoch: epoch has FK to tsa_anchor)
    op.create_table(
        "tsa_anchor",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("anchor_type", sa.String(length=20), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("tsa_token", postgresql.BYTEA(), nullable=False),
        sa.Column("tsa_provider", sa.String(length=100), nullable=False),
        sa.Column("tsa_serial", sa.String(length=100), nullable=True),
        sa.Column(
            "anchored_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "tsa_reported_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.CheckConstraint(
            "anchor_type IN ('EPOCH','BATCH','EVENT')",
            name="chk_tsa_anchor_type",
        ),
        sa.CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','FAILED')",
            name="chk_tsa_verification_status",
        ),
    )
    op.create_index(
        "idx_tsa_tenant",
        "tsa_anchor",
        ["tenant_id", "anchored_at"],
        unique=False,
    )
    op.create_index(
        "idx_tsa_payload",
        "tsa_anchor",
        ["payload_hash"],
        unique=False,
    )

    # 3.4 integrity_epochs
    op.create_table(
        "integrity_epoch",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("epoch_number", sa.BigInteger(), nullable=False),
        sa.Column("genesis_hash", sa.String(length=64), nullable=False),
        sa.Column("terminal_hash", sa.String(length=64), nullable=True),
        sa.Column("first_event_seq", sa.BigInteger(), nullable=False),
        sa.Column("last_event_seq", sa.BigInteger(), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "tsa_anchor_id",
            sa.String(),
            sa.ForeignKey("tsa_anchor.id"),
            nullable=True,
        ),
        sa.Column("merkle_root", sa.String(length=64), nullable=True),
        sa.Column("profile_snapshot", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="OPEN",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "subject_id",
            "epoch_number",
            name="uq_epoch_number",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','SEALED','BROKEN','REPAIRED')",
            name="chk_epoch_status",
        ),
    )
    op.create_index(
        "idx_epochs_open",
        "integrity_epoch",
        ["tenant_id", "subject_id"],
        unique=False,
        postgresql_where=sa.text("status = 'OPEN'"),
    )
    op.create_index(
        "idx_epochs_seal",
        "integrity_epoch",
        ["sealed_at"],
        unique=False,
        postgresql_where=sa.text("status = 'SEALED'"),
    )

    # 3.6 merkle_nodes
    op.create_table(
        "merkle_node",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "epoch_id",
            sa.String(),
            sa.ForeignKey("integrity_epoch.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_hash", sa.String(length=64), nullable=False),
        sa.Column("left_child_hash", sa.String(length=64), nullable=True),
        sa.Column("right_child_hash", sa.String(length=64), nullable=True),
        sa.Column("event_seq", sa.BigInteger(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column(
            "is_root",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint(
            "epoch_id",
            "depth",
            "position",
            name="uq_merkle_position",
        ),
    )
    op.create_index(
        "idx_merkle_epoch",
        "merkle_node",
        ["epoch_id", "depth"],
        unique=False,
    )
    op.create_index(
        "idx_merkle_leaf",
        "merkle_node",
        ["epoch_id", "event_seq"],
        unique=False,
        postgresql_where=sa.text("event_seq IS NOT NULL"),
    )
    op.create_index(
        "idx_merkle_root",
        "merkle_node",
        ["epoch_id"],
        unique=False,
        postgresql_where=sa.text("is_root = true"),
    )

    # 3.7 chain_repair_log
    op.create_table(
        "chain_repair_log",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "epoch_id",
            sa.String(),
            sa.ForeignKey("integrity_epoch.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "break_detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("break_at_event_seq", sa.BigInteger(), nullable=False),
        sa.Column("break_reason", sa.Text(), nullable=False),
        sa.Column(
            "repair_initiated_by",
            sa.String(),
            sa.ForeignKey("app_user.id"),
            nullable=False,
        ),
        sa.Column(
            "repair_approved_by",
            sa.String(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("repair_reference", sa.String(length=100), nullable=True),
        sa.Column("repair_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "new_epoch_id",
            sa.String(),
            sa.ForeignKey("integrity_epoch.id"),
            nullable=True,
        ),
        sa.Column(
            "repair_status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING_APPROVAL",
        ),
        sa.CheckConstraint(
            "repair_status IN "
            "('PENDING_APPROVAL','APPROVED','REJECTED','COMPLETED','FAILED')",
            name="chk_chain_repair_status",
        ),
    )
    op.create_index(
        "idx_repair_tenant",
        "chain_repair_log",
        ["tenant_id", "break_detected_at"],
        unique=False,
    )
    op.create_index(
        "idx_repair_epoch",
        "chain_repair_log",
        ["epoch_id"],
        unique=False,
    )
    op.create_index(
        "idx_repair_open",
        "chain_repair_log",
        ["tenant_id"],
        unique=False,
        postgresql_where=sa.text(
            "repair_status IN ('PENDING_APPROVAL','APPROVED')"
        ),
    )

    # 3.3 events — additions (after integrity_epoch / tsa_anchor exist)
    op.add_column(
        "event",
        sa.Column(
            "epoch_id",
            sa.String(),
            sa.ForeignKey("integrity_epoch.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "event",
        sa.Column(
            "integrity_status",
            sa.String(length=20),
            nullable=False,
            server_default="VALID",
        ),
    )
    op.add_column(
        "event",
        sa.Column(
            "tsa_anchor_id",
            sa.String(),
            sa.ForeignKey("tsa_anchor.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "event",
        sa.Column("merkle_leaf_hash", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "chk_event_integrity_status",
        "event",
        "integrity_status IN "
        "('VALID','CHAIN_BREAK','REPAIRED','ERASED','PENDING_ANCHOR')",
    )
    op.create_index("idx_events_epoch", "event", ["epoch_id"], unique=False)
    op.execute(
        "CREATE INDEX idx_events_integrity ON event (tenant_id, integrity_status) "
        "WHERE integrity_status <> 'VALID'"
    )


def downgrade() -> None:
    # 3.3 events — drop additions
    op.execute("DROP INDEX IF EXISTS idx_events_integrity")
    op.drop_index("idx_events_epoch", table_name="event")
    op.drop_constraint("chk_event_integrity_status", "event", type_="check")
    op.drop_column("event", "merkle_leaf_hash")
    op.drop_column("event", "tsa_anchor_id")
    op.drop_column("event", "integrity_status")
    op.drop_column("event", "epoch_id")

    # 3.7 chain_repair_log
    op.drop_index("idx_repair_open", table_name="chain_repair_log")
    op.drop_index("idx_repair_epoch", table_name="chain_repair_log")
    op.drop_index("idx_repair_tenant", table_name="chain_repair_log")
    op.drop_table("chain_repair_log")

    # 3.6 merkle_nodes
    op.drop_index("idx_merkle_root", table_name="merkle_node")
    op.drop_index("idx_merkle_leaf", table_name="merkle_node")
    op.drop_index("idx_merkle_epoch", table_name="merkle_node")
    op.drop_table("merkle_node")

    # 3.5 tsa_anchors
    op.drop_index("idx_tsa_payload", table_name="tsa_anchor")
    op.drop_index("idx_tsa_tenant", table_name="tsa_anchor")
    op.drop_table("tsa_anchor")

    # 3.4 integrity_epochs
    op.drop_index("idx_epochs_seal", table_name="integrity_epoch")
    op.drop_index("idx_epochs_open", table_name="integrity_epoch")
    op.drop_table("integrity_epoch")

    # 3.2 tenant_integrity_profile_history
    op.drop_index(
        "idx_tip_history_tenant",
        table_name="tenant_integrity_profile_history",
    )
    op.drop_table("tenant_integrity_profile_history")

    # 3.1 tenant — drop additions
    op.execute(
        "COMMENT ON COLUMN tenant.integrity_profile IS NULL"
    )
    op.drop_constraint("chk_integrity_profile", "tenant", type_="check")
    op.drop_column("tenant", "profile_changed_by")
    op.drop_column("tenant", "profile_changed_at")
    op.drop_column("tenant", "integrity_profile")

