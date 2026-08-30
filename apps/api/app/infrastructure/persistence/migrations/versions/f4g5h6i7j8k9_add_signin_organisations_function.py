"""Add the one read the sign-in screen needs before any organisation is known.

Revision ID: f4g5h6i7j8k9
Revises: e3f4g5h6i7j8
Create Date: 2026-08-11

Sign-in asks for an email and needs to know which organisations it belongs to, so
nobody has to type an organisation code. That read happens before any tenant
context exists, and ``app_user`` and ``tenant`` are both behind row-level
security, so an ordinary query from the application role returns nothing.

Rather than punching a policy hole in ``tenant`` (which would expose every
organisation row to every caller), this adds a single SECURITY DEFINER function.
It runs as its owner, so it can see across organisations, but it can only ever
answer one question: "for this exact email, which organisations?" It returns
organisation id and name and nothing about the person.

``search_path`` is pinned, which is required for SECURITY DEFINER functions so a
caller cannot shadow the tables it references.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f4g5h6i7j8k9"
down_revision: str | Sequence[str] | None = "e3f4g5h6i7j8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CREATE_FN = """
CREATE OR REPLACE FUNCTION public.signin_organisations(p_email text)
RETURNS TABLE (tenant_id text, tenant_name text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    SELECT t.id::text, t.name::text
    FROM identity i
    JOIN app_user u ON u.identity_id = i.id
    JOIN tenant t ON t.id = u.tenant_id
    WHERE i.email = lower(btrim(p_email))
      AND i.is_active
      AND u.is_active
      AND t.status = 'Active'
    ORDER BY t.name
$fn$;
"""

# The application role is created by hand per environment (it needs a password),
# so grant only if it is actually present.
_GRANT = """
DO $$
BEGIN
    EXECUTE 'REVOKE ALL ON FUNCTION public.signin_organisations(text) FROM PUBLIC';
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'timeline_app') THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION public.signin_organisations(text) TO timeline_app';
    END IF;
END $$;
"""


def upgrade() -> None:
    """Create signin_organisations and grant it to the application role if present."""
    op.execute(_CREATE_FN)
    op.execute(_GRANT)


def downgrade() -> None:
    """Drop signin_organisations."""
    op.execute("DROP FUNCTION IF EXISTS public.signin_organisations(text)")
