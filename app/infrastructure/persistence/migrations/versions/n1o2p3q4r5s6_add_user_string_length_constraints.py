"""Add string length constraints to app_user

Revision ID: n1o2p3q4r5s6
Revises: h0i1j2k3l4m5
Create Date: 2025-02-11

Adds DB-level max length on username (255), email (255), and hashed_password (96)
to prevent storage abuse. Bcrypt hashes are 60 chars; 96 allows for other algorithms.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "n1o2p3q4r5s6"
down_revision: Union[str, Sequence[str], None] = "h0i1j2k3l4m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "app_user",
        "username",
        existing_type=sa.String(),
        type_=sa.String(255),
        existing_nullable=False,
    )
    op.alter_column(
        "app_user",
        "email",
        existing_type=sa.String(),
        type_=sa.String(255),
        existing_nullable=False,
    )
    op.alter_column(
        "app_user",
        "hashed_password",
        existing_type=sa.String(),
        type_=sa.String(96),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "app_user",
        "hashed_password",
        existing_type=sa.String(96),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.alter_column(
        "app_user",
        "email",
        existing_type=sa.String(255),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.alter_column(
        "app_user",
        "username",
        existing_type=sa.String(255),
        type_=sa.String(),
        existing_nullable=False,
    )
