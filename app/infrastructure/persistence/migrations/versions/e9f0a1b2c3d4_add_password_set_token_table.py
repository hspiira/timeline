"""Add password_set_token table for C2 set-initial-password flow.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-02-17

One-time tokens for POST /auth/set-initial-password (tenant creation C2:
return set_password_url in response, no password in response).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_set_token",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_password_set_token_token_hash"),
        "password_set_token",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_password_set_token_user_id"),
        "password_set_token",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_password_set_token_user_id"), table_name="password_set_token")
    op.drop_index(op.f("ix_password_set_token_token_hash"), table_name="password_set_token")
    op.drop_table("password_set_token")
