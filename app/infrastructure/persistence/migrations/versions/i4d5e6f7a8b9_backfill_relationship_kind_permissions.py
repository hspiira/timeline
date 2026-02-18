"""Backfill permissions for relationship kinds.

Revision ID: i4d5e6f7a8b9
Revises: h3c4d5e6f7a8
Create Date: 2026-02-18

Adds relationship_kind:read, create, update, delete for existing tenants
and assigns them to admin (all), manager (all), agent (read), auditor (read).
New tenants get these from TenantInitializationService.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "i4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "h3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    ("relationship_kind:read", "relationship_kind", "read", "View relationship kinds"),
    ("relationship_kind:create", "relationship_kind", "create", "Create relationship kinds"),
    ("relationship_kind:update", "relationship_kind", "update", "Update relationship kinds"),
    ("relationship_kind:delete", "relationship_kind", "delete", "Delete relationship kinds"),
]


def upgrade() -> None:
    from app.shared.utils.generators import generate_cuid

    conn = op.get_bind()
    tenants = conn.execute(text("SELECT id FROM tenant")).fetchall()
    for (tenant_id,) in tenants:
        existing = conn.execute(
            text(
                "SELECT 1 FROM permission WHERE tenant_id = :tid AND code = 'relationship_kind:read'"
            ),
            {"tid": tenant_id},
        ).fetchone()
        if existing:
            continue

        perm_ids = {}
        for code, resource, action, description in NEW_PERMISSIONS:
            pid = generate_cuid()
            conn.execute(
                text(
                    "INSERT INTO permission (id, tenant_id, code, resource, action, description) "
                    "VALUES (:id, :tenant_id, :code, :resource, :action, :description)"
                ),
                {
                    "id": pid,
                    "tenant_id": tenant_id,
                    "code": code,
                    "resource": resource,
                    "action": action,
                    "description": description,
                },
            )
            perm_ids[code] = pid

        for role_code, permission_codes in [
            ("admin", ["relationship_kind:read", "relationship_kind:create", "relationship_kind:update", "relationship_kind:delete"]),
            ("manager", ["relationship_kind:read", "relationship_kind:create", "relationship_kind:update", "relationship_kind:delete"]),
            ("agent", ["relationship_kind:read"]),
            ("auditor", ["relationship_kind:read"]),
        ]:
            role_row = conn.execute(
                text("SELECT id FROM role WHERE tenant_id = :tid AND code = :code"),
                {"tid": tenant_id, "code": role_code},
            ).fetchone()
            if not role_row:
                continue
            (role_id,) = role_row
            for code in permission_codes:
                rp_id = generate_cuid()
                conn.execute(
                    text(
                        "INSERT INTO role_permission (id, tenant_id, role_id, permission_id) "
                        "VALUES (:id, :tenant_id, :role_id, :permission_id) "
                        "ON CONFLICT ON CONSTRAINT uq_role_permission DO NOTHING"
                    ),
                    {
                        "id": rp_id,
                        "tenant_id": tenant_id,
                        "role_id": role_id,
                        "permission_id": perm_ids[code],
                    },
                )


def downgrade() -> None:
    conn = op.get_bind()
    for code, _, _, _ in NEW_PERMISSIONS:
        conn.execute(
            text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        conn.execute(text("DELETE FROM permission WHERE code = :code"), {"code": code})
