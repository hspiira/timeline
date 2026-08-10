"""Split a person's identity from their organisation membership.

Revision ID: e3f4g5h6i7j8
Revises: d2e3f4g5h6i7
Create Date: 2026-08-11

Before this, ``app_user`` held both who someone is (email, password hash) and
which organisation they belong to (tenant_id), keyed unique on
(tenant_id, email). One human in three organisations therefore had three
password hashes, so there was no single place answering "who is this person and
how do they prove it". Changing a password, disabling a leaver, verifying an
email, or linking a passkey all had to be repeated per organisation.

After this:

* ``identity`` — one row per person, global. Email unique across the whole
  system, holds the password hash. This is the single source of truth for
  credentials and the anchor for future passkey / SSO links.
* ``app_user`` — one row per person *per organisation*. Keeps ``tenant_id`` and
  the tenant-scoped ``username`` handle, gains ``identity_id``, and loses
  ``email`` and ``hashed_password``. Unique on (tenant_id, identity_id).

Emails are stored lower-cased, because a system-wide unique constraint on a
case-sensitive column would let Henry@x and henry@x become two people.

``identity`` deliberately has no ``tenant_id`` and no RLS policy: it holds no
tenant business data, and sign-in must read it before any organisation is known.
It is the single carve-out the sign-in path needs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4g5h6i7j8"
down_revision: str | Sequence[str] | None = "d2e3f4g5h6i7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create identity, move credentials into it, and reduce app_user to a membership."""
    op.create_table(
        "identity",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(96), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("uq_identity_email", "identity", ["email"], unique=True)

    op.add_column("app_user", sa.Column("identity_id", sa.String(), nullable=True))

    # Backfill: one identity per distinct lower-cased email, taking the password
    # hash from that email's earliest membership so the choice is deterministic.
    op.execute(
        """
        INSERT INTO identity (id, email, hashed_password, is_active, created_at, updated_at)
        SELECT DISTINCT ON (lower(email))
               'idn_' || md5(lower(email)),
               lower(email),
               hashed_password,
               is_active,
               now(),
               now()
        FROM app_user
        ORDER BY lower(email), created_at ASC
        """
    )
    op.execute(
        """
        UPDATE app_user u
        SET identity_id = i.id
        FROM identity i
        WHERE i.email = lower(u.email)
        """
    )

    op.drop_constraint("uq_tenant_email", "app_user", type_="unique")
    op.drop_column("app_user", "email")
    op.drop_column("app_user", "hashed_password")

    op.alter_column("app_user", "identity_id", nullable=False)
    op.create_foreign_key(
        "fk_app_user_identity",
        "app_user",
        "identity",
        ["identity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_tenant_identity", "app_user", ["tenant_id", "identity_id"]
    )
    op.create_index("ix_app_user_identity_id", "app_user", ["identity_id"])


def downgrade() -> None:
    """Fold credentials back onto app_user and drop identity.

    Lossy by nature: an identity with no membership cannot be represented on
    app_user and is discarded.
    """
    op.add_column("app_user", sa.Column("email", sa.String(255), nullable=True))
    op.add_column(
        "app_user", sa.Column("hashed_password", sa.String(96), nullable=True)
    )
    op.execute(
        """
        UPDATE app_user u
        SET email = i.email, hashed_password = i.hashed_password
        FROM identity i
        WHERE i.id = u.identity_id
        """
    )
    op.alter_column("app_user", "email", nullable=False)
    op.alter_column("app_user", "hashed_password", nullable=False)

    op.drop_index("ix_app_user_identity_id", table_name="app_user")
    op.drop_constraint("uq_tenant_identity", "app_user", type_="unique")
    op.drop_constraint("fk_app_user_identity", "app_user", type_="foreignkey")
    op.drop_column("app_user", "identity_id")
    op.create_unique_constraint("uq_tenant_email", "app_user", ["tenant_id", "email"])

    op.drop_index("uq_identity_email", table_name="identity")
    op.drop_table("identity")
