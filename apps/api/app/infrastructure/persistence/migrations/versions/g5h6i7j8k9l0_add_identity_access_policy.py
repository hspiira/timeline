"""Give ``identity`` an explicit access policy, because the platform forces RLS on.

Revision ID: g5h6i7j8k9l0
Revises: f4g5h6i7j8k9
Create Date: 2026-08-11

``identity`` is deliberately not tenant-scoped: it is one row per person, holding
the credential, and sign-in must read it before any organisation is known. The
plan was therefore to leave row-level security off it.

That is not possible on Supabase. The platform installs an event trigger
(``ensure_rls``, calling ``rls_auto_enable``) that fires on ``ddl_command_end`` and
enables row-level security on every new table in ``public``. So ``identity`` was
created with RLS already on and no policy attached, which denies every read and
write — the symptom being "new row violates row-level security policy for table
identity" when creating a tenant's first admin.

Since RLS cannot be kept off, this states the intent explicitly instead: a
permissive policy meaning "this table is not partitioned by organisation". Access
to it is controlled by table grants and by the application, not by a tenant
predicate — there is no tenant column to write one against.

Consequence worth being clear about: the application role can read every row here,
including password hashes, where previously hashes sat in the tenant-scoped
``app_user``. Bcrypt hashes are not directly usable, but the blast radius is wider
than before. Narrowing it further means routing every credential read through a
SECURITY DEFINER function and revoking the application's direct SELECT, which is a
larger change and is not attempted here.

Note for future migrations: any new table in ``public`` on Supabase arrives with
RLS enabled and no policy, so it will silently reject all access until a policy is
added. Do not assume a new table is reachable just because you created it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "g5h6i7j8k9l0"
down_revision: str | Sequence[str] | None = "f4g5h6i7j8k9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Attach a permissive policy to identity so the application can use it."""
    op.execute("ALTER TABLE identity ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS identity_not_tenant_scoped ON identity")
    op.execute(
        "CREATE POLICY identity_not_tenant_scoped ON identity "
        "USING (true) WITH CHECK (true)"
    )


def downgrade() -> None:
    """Remove the policy, which leaves identity unreachable while RLS stays on."""
    op.execute("DROP POLICY IF EXISTS identity_not_tenant_scoped ON identity")
