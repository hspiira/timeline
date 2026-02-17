"""Backfill permissions for insider-abuse mitigations.

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-02-17

Adds role:manage_permissions, user_role:read, user_role:update, user_role:assign_admin
for existing tenants and assigns them to admin/manager roles so that:
- Only admins can assign/remove permissions to/from roles.
- Only admins can assign/remove the admin role; managers can assign/remove non-admin roles.
New tenants get these from TenantInitializationService; this migration backfills existing tenants.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New permissions: (code, resource, action, description)
NEW_PERMISSIONS = [
    ("role:manage_permissions", "role", "manage_permissions", "Assign/remove permissions to/from roles (admin-only)"),
    ("user_role:read", "user_role", "read", "View user role assignments"),
    ("user_role:update", "user_role", "update", "Assign/remove non-admin roles to/from users"),
    ("user_role:assign_admin", "user_role", "assign_admin", "Assign or remove admin role (admin-only)"),
]


def upgrade() -> None:
    from app.shared.utils.generators import generate_cuid

    conn = op.get_bind()
    tenants = conn.execute(text("SELECT id FROM tenant")).fetchall()
    for (tenant_id,) in tenants:
        # Skip if this tenant already has the new permission (e.g. created after code change)
        existing = conn.execute(
            text("SELECT 1 FROM permission WHERE tenant_id = :tid AND code = 'role:manage_permissions'"),
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

        # Admin role: add role:manage_permissions and user_role:assign_admin
        admin_role = conn.execute(
            text("SELECT id FROM role WHERE tenant_id = :tid AND code = 'admin'"),
            {"tid": tenant_id},
        ).fetchone()
        if admin_role:
            (admin_rid,) = admin_role
            for code in ("role:manage_permissions", "user_role:assign_admin"):
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
                        "role_id": admin_rid,
                        "permission_id": perm_ids[code],
                    },
                )
        # Manager role: add user_role:read and user_role:update
        manager_role = conn.execute(
            text("SELECT id FROM role WHERE tenant_id = :tid AND code = 'manager'"),
            {"tid": tenant_id},
        ).fetchone()
        if manager_role:
            (manager_rid,) = manager_role
            for code in ("user_role:read", "user_role:update"):
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
                        "role_id": manager_rid,
                        "permission_id": perm_ids[code],
                    },
                )


def downgrade() -> None:
    # Remove the new permissions and their role_permission rows (by code)
    conn = op.get_bind()
    for code, _, _, _ in NEW_PERMISSIONS:
        conn.execute(text("DELETE FROM role_permission WHERE permission_id IN (SELECT id FROM permission WHERE code = :code)"), {"code": code})
        conn.execute(text("DELETE FROM permission WHERE code = :code"), {"code": code})
