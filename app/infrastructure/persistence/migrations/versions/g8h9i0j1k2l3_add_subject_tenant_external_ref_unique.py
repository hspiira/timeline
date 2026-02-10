"""add subject (tenant_id, external_ref) unique constraint

Revision ID: g8h9i0j1k2l3
Revises: a0b1c2d3e4f5
Create Date: 2025-02-10

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g8h9i0j1k2l3"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on (tenant_id, external_ref) for subject."""
    op.create_unique_constraint(
        "uq_subject_tenant_external_ref",
        "subject",
        ["tenant_id", "external_ref"],
    )


def downgrade() -> None:
    """Remove unique constraint on (tenant_id, external_ref)."""
    op.drop_constraint(
        "uq_subject_tenant_external_ref",
        "subject",
        type_="unique",
    )
