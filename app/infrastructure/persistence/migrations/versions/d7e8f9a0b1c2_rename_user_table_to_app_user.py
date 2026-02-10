"""rename user table to app_user

Avoid using PostgreSQL reserved keyword 'user' as table name.
Revision ID: d7e8f9a0b1c2
Revises: 0808a66fe6bf
Create Date: (generated)

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "0808a66fe6bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("user", "app_user")


def downgrade() -> None:
    op.rename_table("app_user", "user")
