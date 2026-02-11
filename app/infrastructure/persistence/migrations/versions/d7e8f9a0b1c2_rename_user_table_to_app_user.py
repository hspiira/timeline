"""rename user table to app_user

Avoid using PostgreSQL reserved keyword 'user' as table name.
Revision ID: d7e8f9a0b1c2
Revises: 0808a66fe6bf
Create Date: (generated)

"""

from collections.abc import Sequence
from typing import Union


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "0808a66fe6bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table created as app_user in e86ff0b3330d to avoid PostgreSQL reserved word "user".
    pass


def downgrade() -> None:
    # Table was always app_user; no rename to revert.
    pass
